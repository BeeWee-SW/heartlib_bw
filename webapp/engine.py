"""Model management and generation.

``torch`` and ``heartlib`` are imported inside functions on purpose: the server
has to start and serve a useful setup screen on a machine where neither is
installed yet.
"""

from __future__ import annotations

import json
import random
import threading
import time
from pathlib import Path
from typing import Any, Callable

from . import checkpoints
from .config import FRAME_MS, MAX_SEQ_LEN, SAMPLE_RATE, AppConfig
from .presets import normalize_tags
from .progress import JobCancelled, track_decoding, track_generation

DTYPE_NAMES = {"bf16": "bfloat16", "fp16": "float16", "fp32": "float32"}


# --------------------------------------------------------------------------
# Environment probing
# --------------------------------------------------------------------------
def torch_status() -> dict:
    """What the host can actually run — never raises."""
    try:
        import torch
    except ImportError:
        return {"installed": False, "version": None, "cuda": False, "devices": ["cpu"], "gpus": []}

    devices = ["cpu"]
    gpus = []
    cuda = bool(torch.cuda.is_available())
    if cuda:
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            devices.insert(i, f"cuda:{i}")
            gpus.append({"index": i, "name": props.name, "total_bytes": props.total_memory})
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        devices.append("mps")
    return {
        "installed": True,
        "version": torch.__version__,
        "cuda": cuda,
        "devices": devices,
        "gpus": gpus,
    }


def heartlib_installed() -> bool:
    from importlib.util import find_spec

    try:
        return find_spec("heartlib") is not None
    except (ImportError, ValueError):
        return False


def available_audio_formats() -> list[str]:
    """WAV and FLAC go through soundfile; MP3 needs an ffmpeg backend."""
    formats = ["wav", "flac"]
    try:
        import torchaudio

        backends = set(torchaudio.list_audio_backends())
        if "ffmpeg" in backends:
            formats.append("mp3")
    except Exception:
        pass
    return formats


def max_duration_s(prompt_tokens: int = 0) -> int:
    """Hard ceiling from the backbone's 8192-frame context at 80 ms per frame."""
    usable = max(MAX_SEQ_LEN - prompt_tokens - 16, 0)
    return int(usable * FRAME_MS / 1000)


# --------------------------------------------------------------------------
# Pipeline subclass
# --------------------------------------------------------------------------
def _studio_pipeline_class():
    """Build the subclass lazily so importing this module never needs torch."""
    import torch
    import torchaudio
    from heartlib import HeartMuLaGenPipeline

    class StudioPipeline(HeartMuLaGenPipeline):
        """Adds seeding and exposes the vocoder knobs the CLI hides.

        ``_sanitize_parameters`` (music_generation.py:183) only forwards five
        keyword arguments, and ``postprocess`` calls ``detokenize`` without any
        of its quality settings (music_generation.py:340).  Overriding those two
        hooks keeps the upstream orchestration in ``__call__`` intact.
        """

        def _sanitize_parameters(self, **kwargs):
            pre, fwd, post = super()._sanitize_parameters(**kwargs)
            fwd["seed"] = kwargs.get("seed")
            post["seed"] = kwargs.get("seed")
            post["num_steps"] = kwargs.get("num_steps", 10)
            post["guidance_scale"] = kwargs.get("codec_guidance_scale", 1.25)
            return pre, fwd, post

        def _forward(self, model_inputs, *, seed=None, **kwargs):
            if seed is not None:
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed)
            return super()._forward(model_inputs, **kwargs)

        def postprocess(
            self,
            model_outputs,
            save_path,
            seed=None,
            num_steps=10,
            guidance_scale=1.25,
        ):
            # The decoder draws its own flow-matching noise
            # (modeling_heartcodec.py:67), so it needs seeding too. A distinct
            # offset keeps it from mirroring the language model's stream.
            if seed is not None:
                torch.manual_seed(seed + 1)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed + 1)
            frames = model_outputs["frames"].to(self.codec_device)
            wav = self.codec.detokenize(
                frames, num_steps=num_steps, guidance_scale=guidance_scale
            )
            self._unload()
            torchaudio.save(save_path, wav.to(torch.float32).cpu(), SAMPLE_RATE)

    return StudioPipeline


# --------------------------------------------------------------------------
# Model manager
# --------------------------------------------------------------------------
class ModelManager:
    """Keeps one pipeline warm; ~7 GB of weights must not be reloaded per song."""

    def __init__(self) -> None:
        self._pipeline: Any = None
        self._signature: tuple | None = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._pipeline is not None

    def describe(self) -> dict:
        if not self._signature:
            return {"loaded": False}
        version, mula_device, codec_device, mula_dtype, codec_dtype, lazy_load = self._signature
        return {
            "loaded": self.loaded,
            "version": version,
            "mula_device": mula_device,
            "codec_device": codec_device,
            "mula_dtype": mula_dtype,
            "codec_dtype": codec_dtype,
            "lazy_load": lazy_load,
        }

    def get(
        self,
        config: AppConfig,
        *,
        version: str,
        mula_device: str,
        codec_device: str,
        mula_dtype: str,
        codec_dtype: str,
        lazy_load: bool,
        on_stage: Callable[[str], None] | None = None,
    ):
        import torch

        signature = (version, mula_device, codec_device, mula_dtype, codec_dtype, lazy_load)
        with self._lock:
            if self._pipeline is not None and self._signature == signature:
                return self._pipeline
            if self._pipeline is not None:
                self._drop()

            if on_stage:
                on_stage("load_model")

            state = checkpoints.describe(config)
            if not state["ready"]:
                missing = [c["id"] for c in state["components"] if not c["present"]]
                raise CheckpointsMissing(missing)

            # lazy_load frees modules via torch.cuda calls (music_generation.py:160),
            # which are meaningless without CUDA.
            if lazy_load and not torch.cuda.is_available():
                lazy_load = False

            cls = _studio_pipeline_class()
            self._pipeline = cls.from_pretrained(
                str(config.ckpt_root),
                device={
                    "mula": torch.device(mula_device),
                    "codec": torch.device(codec_device),
                },
                dtype={
                    "mula": getattr(torch, DTYPE_NAMES[mula_dtype]),
                    "codec": getattr(torch, DTYPE_NAMES[codec_dtype]),
                },
                version=version,
                lazy_load=lazy_load,
            )
            self._signature = signature
            return self._pipeline

    def unload(self) -> None:
        with self._lock:
            self._drop()

    def _drop(self) -> None:
        import gc

        self._pipeline = None
        self._signature = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


class CheckpointsMissing(RuntimeError):
    def __init__(self, missing: list[str]) -> None:
        super().__init__("checkpoints_missing: " + ", ".join(missing))
        self.missing = missing


_manager: ModelManager | None = None


def get_manager() -> ModelManager:
    global _manager
    if _manager is None:
        _manager = ModelManager()
    return _manager


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------
def estimate_prompt_tokens(tags: str, lyrics: str) -> int:
    """Rough token count, used only to warn about the context ceiling."""
    return int((len(tags) + len(lyrics)) / 3.2) + 8


def generate(
    config: AppConfig,
    request: dict,
    model_settings: dict,
    on_stage: Callable[[str, float, str], None],
    should_cancel: Callable[[], bool],
) -> dict:
    """Run one generation end to end and return the history entry."""
    import torch

    manager = get_manager()
    on_stage("load_model", 0.0, "")
    pipeline = manager.get(
        config,
        version=model_settings.get("version", "3B"),
        mula_device=model_settings.get("mula_device", "cuda"),
        codec_device=model_settings.get("codec_device", "cuda"),
        mula_dtype=model_settings.get("mula_dtype", "bf16"),
        codec_dtype=model_settings.get("codec_dtype", "fp32"),
        lazy_load=model_settings.get("lazy_load", False),
    )
    if should_cancel():
        raise JobCancelled()

    tags = normalize_tags(request["tags"])
    lyrics = request["lyrics"]
    seed = request.get("seed")
    if seed is None:
        seed = random.randrange(0, 2**32 - 1)

    duration_s = int(request["duration_s"])
    max_audio_length_ms = duration_s * 1000
    frames_total = max_audio_length_ms // FRAME_MS
    num_steps = int(request.get("num_steps", 10))

    audio_format = request.get("audio_format", "wav")
    started = time.time()
    job_id = request["job_id"]
    save_path = config.output_dir / f"{job_id}.{audio_format}"

    # The generation loop covers the bulk of the runtime; decoding is a
    # smaller, roughly fixed tail. Weighting them keeps the bar honest.
    def lm_progress(fraction: float, done: int, total: int) -> None:
        on_stage("generate", 0.05 + fraction * 0.75, f"{done}/{total}")

    def decode_progress(fraction: float) -> None:
        on_stage("decode", 0.80 + fraction * 0.18, "")

    on_stage("generate", 0.05, "")
    with torch.no_grad():
        with track_generation(lm_progress, should_cancel):
            with track_decoding(frames_total, num_steps, decode_progress, should_cancel):
                pipeline(
                    {"lyrics": lyrics, "tags": tags},
                    max_audio_length_ms=max_audio_length_ms,
                    save_path=str(save_path),
                    topk=int(request["topk"]),
                    temperature=float(request["temperature"]),
                    cfg_scale=float(request["cfg_scale"]),
                    seed=seed,
                    num_steps=num_steps,
                    codec_guidance_scale=float(request.get("codec_guidance_scale", 1.25)),
                )

    on_stage("save", 0.99, "")
    size = save_path.stat().st_size if save_path.exists() else 0
    entry = {
        "id": job_id,
        "title": request.get("title") or _derive_title(lyrics, tags),
        "created_at": time.time(),
        "duration_request_s": duration_s,
        "generation_s": round(time.time() - started, 1),
        "file": save_path.name,
        "bytes": size,
        "audio_format": audio_format,
        "settings": {
            "tags": tags,
            "lyrics": lyrics,
            "duration_s": duration_s,
            "temperature": float(request["temperature"]),
            "topk": int(request["topk"]),
            "cfg_scale": float(request["cfg_scale"]),
            "seed": seed,
            "num_steps": num_steps,
            "codec_guidance_scale": float(request.get("codec_guidance_scale", 1.25)),
            "audio_format": audio_format,
        },
        "model": manager.describe(),
    }
    append_history(config, entry)
    return entry


def _derive_title(lyrics: str, tags: str) -> str:
    for line in lyrics.splitlines():
        line = line.strip()
        if line and not line.startswith("["):
            return line[:60]
    return (tags.split(",")[0] if tags else "Untitled").title()


# --------------------------------------------------------------------------
# History
# --------------------------------------------------------------------------
_history_lock = threading.Lock()


def read_history(config: AppConfig) -> list[dict]:
    path = config.history_file
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def append_history(config: AppConfig, entry: dict) -> None:
    with _history_lock:
        history = read_history(config)
        history.insert(0, entry)
        config.history_file.write_text(
            json.dumps(history[:200], ensure_ascii=False, indent=2), encoding="utf-8"
        )


def delete_history_entry(config: AppConfig, entry_id: str) -> bool:
    with _history_lock:
        history = read_history(config)
        remaining = [e for e in history if e.get("id") != entry_id]
        if len(remaining) == len(history):
            return False
        for entry in history:
            if entry.get("id") == entry_id:
                target = config.output_dir / str(entry.get("file", ""))
                if target.is_file() and target.parent == config.output_dir:
                    target.unlink(missing_ok=True)
        config.history_file.write_text(
            json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True


def audio_path(config: AppConfig, entry_id: str) -> Path | None:
    for entry in read_history(config):
        if entry.get("id") == entry_id:
            candidate = config.output_dir / str(entry.get("file", ""))
            if candidate.is_file() and candidate.parent == config.output_dir:
                return candidate
    return None

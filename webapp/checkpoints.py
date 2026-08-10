"""Detection and download of the model checkpoints.

The pipeline resolves checkpoints from plain local paths and raises
``FileNotFoundError`` when something is missing (music_generation.py:15-39).
The server needs to *report* that instead of crashing, so the presence checks
below mirror those conditions without calling the upstream helper.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .config import AppConfig

ProgressFn = Callable[[float, str], None]


@dataclass(frozen=True)
class Component:
    """One downloadable checkpoint bundle."""

    id: str
    hf_repo: str
    ms_repo: str
    # Path of the component relative to the checkpoint root.
    subdir: str
    # Files that must exist (relative to the root) for the component to count
    # as present.
    required: tuple[str, ...]
    label_de: str
    label_en: str


COMPONENTS: tuple[Component, ...] = (
    Component(
        id="gen",
        hf_repo="HeartMuLa/HeartMuLaGen",
        ms_repo="HeartMuLa/HeartMuLaGen",
        subdir=".",
        required=("tokenizer.json", "gen_config.json"),
        label_de="Tokenizer & Generierungs-Konfiguration",
        label_en="Tokenizer & generation config",
    ),
    Component(
        id="mula-3b",
        hf_repo="HeartMuLa/HeartMuLa-oss-3B-happy-new-year",
        ms_repo="HeartMuLa/HeartMuLa-oss-3B-happy-new-year",
        subdir="HeartMuLa-oss-3B",
        required=("HeartMuLa-oss-3B",),
        label_de="HeartMuLa 3B (Sprachmodell)",
        label_en="HeartMuLa 3B (language model)",
    ),
    Component(
        id="codec",
        hf_repo="HeartMuLa/HeartCodec-oss-20260123",
        ms_repo="HeartMuLa/HeartCodec-oss-20260123",
        subdir="HeartCodec-oss",
        required=("HeartCodec-oss",),
        label_de="HeartCodec (Audio-Decoder)",
        label_en="HeartCodec (audio decoder)",
    ),
)

COMPONENTS_BY_ID = {c.id: c for c in COMPONENTS}


def _is_present(component: Component, root: Path) -> bool:
    for entry in component.required:
        target = root / entry
        if entry.endswith(".json"):
            if not target.is_file():
                return False
        elif not target.is_dir() or not any(target.iterdir()):
            return False
    return True


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def describe(config: AppConfig) -> dict:
    """Report which components are on disk and how much space they take."""
    root = config.ckpt_root
    components = []
    for component in COMPONENTS:
        present = _is_present(component, root)
        if component.subdir == ".":
            local_bytes = sum(_dir_size(root / f) for f in component.required)
        else:
            local_bytes = _dir_size(root / component.subdir)
        components.append(
            {
                "id": component.id,
                "label": {"de": component.label_de, "en": component.label_en},
                "hf_repo": component.hf_repo,
                "ms_repo": component.ms_repo,
                "target": str(root / component.subdir) if component.subdir != "." else str(root),
                "present": present,
                "local_bytes": local_bytes,
            }
        )
    return {
        "root": str(root),
        "ready": all(c["present"] for c in components),
        "components": components,
        "free_bytes": shutil.disk_usage(root.parent if root.exists() else Path.cwd()).free,
    }


def remote_sizes(components: Iterable[Component] | None = None) -> dict[str, dict]:
    """Ask Hugging Face how large each repo is.

    Runs on the machine that will do the download, because the size only
    matters there — and because huggingface.co is not necessarily reachable
    from wherever the code was written.  A failure is reported per component
    instead of aborting the whole request.
    """
    result: dict[str, dict] = {}
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return {c.id: {"bytes": None, "error": "huggingface_hub_missing"} for c in (components or COMPONENTS)}

    api = HfApi()
    for component in components or COMPONENTS:
        try:
            info = api.model_info(component.hf_repo, files_metadata=True)
            total = sum(getattr(s, "size", None) or 0 for s in (info.siblings or []))
            result[component.id] = {"bytes": total or None, "error": None}
        except Exception as exc:  # network, auth, rename — all non-fatal here
            result[component.id] = {"bytes": None, "error": type(exc).__name__}
    return result


class _ProgressTqdm:
    """A tqdm stand-in that forwards byte counts to a callback.

    ``snapshot_download`` accepts a ``tqdm_class``; it instantiates one bar per
    file plus one for the overall count.  Summing ``n`` across every live bar
    is close enough for a progress display and needs no knowledge of hub
    internals.
    """

    _registry: list["_ProgressTqdm"] = []
    _callback: ProgressFn | None = None
    _label: str = ""

    def __init__(self, *args, **kwargs):
        self.total = kwargs.get("total") or 0
        self.n = 0
        self.unit = kwargs.get("unit", "")
        self.disable = bool(kwargs.get("disable", False))
        self._iterable = args[0] if args else kwargs.get("iterable")
        # Only byte-counting bars are interesting; the file-count bar reports a
        # unit of "it" and would distort the total.
        self._counts = self.unit in {"B", "iB"} and not self.disable
        if self._counts:
            _ProgressTqdm._registry.append(self)

    # -- tqdm surface used by huggingface_hub -----------------------------
    def update(self, n: float = 1) -> None:
        self.n += n
        self._emit()

    def close(self) -> None:
        self._emit()

    def refresh(self, *args, **kwargs) -> None:
        self._emit()

    def set_description(self, *args, **kwargs) -> None:
        pass

    def set_postfix(self, *args, **kwargs) -> None:
        pass

    def __iter__(self):
        for item in self._iterable or ():
            yield item
            self.update(1)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def _emit(self) -> None:
        callback = _ProgressTqdm._callback
        if callback is None:
            return
        done = sum(bar.n for bar in _ProgressTqdm._registry)
        total = sum(bar.total for bar in _ProgressTqdm._registry)
        fraction = min(done / total, 1.0) if total else 0.0
        callback(fraction, f"{_ProgressTqdm._label} {done / 1e9:.2f} / {total / 1e9:.2f} GB".strip())

    @classmethod
    def bind(cls, callback: ProgressFn | None, label: str = "") -> None:
        cls._registry = []
        cls._callback = callback
        cls._label = label


def download(
    config: AppConfig,
    source: str = "huggingface",
    component_ids: list[str] | None = None,
    progress: ProgressFn | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> dict:
    """Fetch the missing checkpoints, resuming any partial download.

    Tries Hugging Face first and falls back to ModelScope (already a
    dependency of heartlib) when the hub is unreachable.
    """
    root = config.ckpt_root
    root.mkdir(parents=True, exist_ok=True)

    wanted = [COMPONENTS_BY_ID[cid] for cid in component_ids] if component_ids else list(COMPONENTS)
    todo = [c for c in wanted if not _is_present(c, root)]
    if not todo:
        return {"downloaded": [], "skipped": [c.id for c in wanted]}

    downloaded: list[str] = []
    for index, component in enumerate(todo):
        if should_cancel and should_cancel():
            raise RuntimeError("cancelled")

        target = root if component.subdir == "." else root / component.subdir
        target.mkdir(parents=True, exist_ok=True)

        def report(fraction: float, message: str) -> None:
            if progress:
                overall = (index + min(fraction, 1.0)) / len(todo)
                progress(overall, message)

        report(0.0, component.hf_repo)
        order = ["huggingface", "modelscope"] if source == "huggingface" else ["modelscope", "huggingface"]
        errors: list[str] = []
        for attempt in order:
            try:
                if attempt == "huggingface":
                    _download_hf(component, target, report)
                else:
                    _download_ms(component, target, report)
                break
            except Exception as exc:
                errors.append(f"{attempt}: {exc}")
        else:
            raise RuntimeError(
                f"Download of {component.id} failed. " + " | ".join(errors)
            )
        downloaded.append(component.id)

    if progress:
        progress(1.0, "")
    return {"downloaded": downloaded, "skipped": [c.id for c in wanted if c not in todo]}


def _download_hf(component: Component, target: Path, report: ProgressFn) -> None:
    from huggingface_hub import snapshot_download

    _ProgressTqdm.bind(report, component.hf_repo)
    try:
        snapshot_download(
            repo_id=component.hf_repo,
            local_dir=str(target),
            tqdm_class=_ProgressTqdm,
        )
    finally:
        _ProgressTqdm.bind(None)


def _download_ms(component: Component, target: Path, report: ProgressFn) -> None:
    from modelscope import snapshot_download as ms_snapshot_download

    report(0.0, f"ModelScope: {component.ms_repo}")
    ms_snapshot_download(component.ms_repo, local_dir=str(target))
    report(1.0, "")


def cli_commands(config: AppConfig, source: str = "huggingface") -> list[str]:
    """The equivalent shell commands, offered as a copyable fallback."""
    root = config.ckpt_root
    lines = []
    for component in COMPONENTS:
        target = root if component.subdir == "." else root / component.subdir
        if source == "modelscope":
            lines.append(f"modelscope download --model '{component.ms_repo}' --local_dir '{target}'")
        else:
            lines.append(f"hf download --local-dir '{target}' '{component.hf_repo}'")
    return lines

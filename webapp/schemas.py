"""Request/response models. Every limit is enforced here, not just in the UI."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

DTYPES = Literal["bf16", "fp16", "fp32"]
AUDIO_FORMATS = Literal["wav", "flac", "mp3"]

# Defaults mirror the CLI in examples/run_music_generation.py:42-50, except for
# the duration, where 120 s is a friendlier starting point than 240 s given
# generation runs at roughly real time.
DEFAULTS: dict[str, Any] = {
    "duration_s": 120,
    "temperature": 1.0,
    "topk": 50,
    "cfg_scale": 1.5,
    "num_steps": 10,
    "codec_guidance_scale": 1.25,
    "audio_format": "wav",
    "mula_dtype": "bf16",
    "codec_dtype": "fp32",
    "lazy_load": False,
}

# Slider bounds handed to the frontend so the UI cannot drift from the server.
RANGES: dict[str, dict[str, float]] = {
    "duration_s": {"min": 15, "max": 300, "step": 5},
    "temperature": {"min": 0.1, "max": 2.0, "step": 0.05},
    "topk": {"min": 1, "max": 200, "step": 1},
    # CFG is only applied above 1.0 (modeling_heartmula.py:198,226) while the
    # batch already doubles at any value != 1.0 (music_generation.py:251), so
    # values below 1.0 would cost time without any effect.
    "cfg_scale": {"min": 1.0, "max": 3.0, "step": 0.1},
    "num_steps": {"min": 5, "max": 50, "step": 1},
    "codec_guidance_scale": {"min": 1.0, "max": 3.0, "step": 0.05},
}

MAX_SEED = 2**32 - 1
MAX_TAGS_CHARS = 4000
MAX_LYRICS_CHARS = 20000


class GenerateRequest(BaseModel):
    # Length is checked in the route so the client gets a translatable code
    # instead of a generic pydantic validation payload.
    tags: str
    lyrics: str
    duration_s: int = Field(default=DEFAULTS["duration_s"], ge=15, le=300)
    temperature: float = Field(default=DEFAULTS["temperature"], ge=0.1, le=2.0)
    topk: int = Field(default=DEFAULTS["topk"], ge=1, le=200)
    cfg_scale: float = Field(default=DEFAULTS["cfg_scale"], ge=1.0, le=3.0)
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED)
    num_steps: int = Field(default=DEFAULTS["num_steps"], ge=5, le=50)
    codec_guidance_scale: float = Field(
        default=DEFAULTS["codec_guidance_scale"], ge=1.0, le=3.0
    )
    audio_format: AUDIO_FORMATS = DEFAULTS["audio_format"]
    title: str | None = Field(default=None, max_length=120)


class ModelLoadRequest(BaseModel):
    mula_device: str = "cuda"
    codec_device: str = "cuda"
    mula_dtype: DTYPES = DEFAULTS["mula_dtype"]
    codec_dtype: DTYPES = DEFAULTS["codec_dtype"]
    lazy_load: bool = DEFAULTS["lazy_load"]
    version: str = "3B"

    @field_validator("mula_device", "codec_device")
    @classmethod
    def _device_shape(cls, value: str) -> str:
        value = value.strip().lower()
        head = value.split(":", 1)[0]
        if head not in {"cuda", "cpu", "mps"}:
            raise ValueError("unsupported device")
        return value


class DownloadRequest(BaseModel):
    source: Literal["huggingface", "modelscope"] = "huggingface"
    components: list[str] | None = None


class TagPreviewRequest(BaseModel):
    tags: str = ""

"""Runtime configuration for the studio server."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"

# 12.5 Hz codec frame rate; the model backbone caps the sequence at 8192 frames
# (see src/heartlib/heartmula/modeling_heartmula.py:18).  Every frame is 80 ms
# (see music_generation.py:314).
FRAME_MS = 80
MAX_SEQ_LEN = 8192
SAMPLE_RATE = 48000


@dataclass
class AppConfig:
    """Everything the server needs to know about its surroundings."""

    ckpt_root: Path = field(default_factory=lambda: REPO_ROOT / "ckpt")
    output_dir: Path = field(default_factory=lambda: REPO_ROOT / "outputs")
    version: str = "3B"
    mula_device: str = "cuda"
    codec_device: str = "cuda"
    mula_dtype: str = "bf16"
    codec_dtype: str = "fp32"
    lazy_load: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    hf_endpoint: str | None = None

    def __post_init__(self) -> None:
        self.ckpt_root = Path(self.ckpt_root).expanduser().resolve()
        self.output_dir = Path(self.output_dir).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.hf_endpoint:
            os.environ["HF_ENDPOINT"] = self.hf_endpoint

    @property
    def history_file(self) -> Path:
        return self.output_dir / "history.json"


_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Return the process-wide config, creating a default one if needed."""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def set_config(config: AppConfig) -> AppConfig:
    global _config
    _config = config
    return _config

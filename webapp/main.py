"""Entry point: python -m webapp.main [options]"""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from .config import REPO_ROOT, AppConfig, set_config


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m webapp.main",
        description="HeartMuLa Studio — local web UI for the HeartMuLa music model.",
    )
    parser.add_argument("--model_path", type=Path, default=REPO_ROOT / "ckpt",
                        help="Checkpoint root (default: ./ckpt)")
    parser.add_argument("--output_dir", type=Path, default=REPO_ROOT / "outputs",
                        help="Where generated songs are written (default: ./outputs)")
    parser.add_argument("--version", default="3B", help="HeartMuLa version folder suffix")
    parser.add_argument("--mula_device", default="cuda")
    parser.add_argument("--codec_device", default="cuda")
    parser.add_argument("--mula_dtype", default="bf16", choices=["bf16", "fp16", "fp32"])
    parser.add_argument("--codec_dtype", default="fp32", choices=["bf16", "fp16", "fp32"])
    parser.add_argument("--lazy_load", action="store_true",
                        help="Load and free modules on demand to save VRAM")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--hf_endpoint", default=None,
                        help="Alternative Hugging Face mirror, e.g. https://hf-mirror.com")
    parser.add_argument("--open", action="store_true", help="Open a browser on start")
    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> AppConfig:
    return set_config(
        AppConfig(
            ckpt_root=args.model_path,
            output_dir=args.output_dir,
            version=args.version,
            mula_device=args.mula_device,
            codec_device=args.codec_device,
            mula_dtype=args.mula_dtype,
            codec_dtype=args.codec_dtype,
            lazy_load=args.lazy_load,
            host=args.host,
            port=args.port,
            hf_endpoint=args.hf_endpoint,
        )
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = build_config(args)

    import uvicorn

    from .routes import app

    url = f"http://{'127.0.0.1' if config.host in {'0.0.0.0', '::'} else config.host}:{config.port}"
    print(f"\n  HeartMuLa Studio  ->  {url}")
    print(f"  Checkpoints: {config.ckpt_root}")
    print(f"  Output:      {config.output_dir}\n")
    if args.open:
        webbrowser.open(url)

    uvicorn.run(app, host=config.host, port=config.port, log_level="info")


if __name__ == "__main__":
    main()

"""FastAPI application and all HTTP endpoints."""

from __future__ import annotations

import json
import mimetypes
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import checkpoints, engine, presets
from .config import STATIC_DIR, get_config
from .jobs import CancelledError, Job, get_queue
from .progress import JobCancelled
from .schemas import (
    DEFAULTS,
    MAX_LYRICS_CHARS,
    MAX_TAGS_CHARS,
    RANGES,
    DownloadRequest,
    GenerateRequest,
    ModelLoadRequest,
    TagPreviewRequest,
)

app = FastAPI(title="HeartMuLa Studio", docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"code": "error.internal", "detail": f"{type(exc).__name__}: {exc}"},
    )


# --------------------------------------------------------------------------
# Status and static data
# --------------------------------------------------------------------------
@app.get("/api/status")
def status() -> dict:
    config = get_config()
    torch_info = engine.torch_status()
    ckpt = checkpoints.describe(config)
    manager = engine.get_manager()
    return {
        "version": "1.0.0",
        "torch": torch_info,
        "heartlib_installed": engine.heartlib_installed(),
        "checkpoints": ckpt,
        "model": manager.describe(),
        "audio_formats": engine.available_audio_formats(),
        "defaults": {
            **DEFAULTS,
            "mula_device": config.mula_device,
            "codec_device": config.codec_device,
            "version": config.version,
        },
        "ranges": RANGES,
        "limits": {
            "max_duration_s": engine.max_duration_s(),
            "max_tags_chars": MAX_TAGS_CHARS,
            "max_lyrics_chars": MAX_LYRICS_CHARS,
        },
        "can_generate": bool(
            torch_info["installed"] and engine.heartlib_installed() and ckpt["ready"]
        ),
        "active_job": (get_queue().active().snapshot() if get_queue().active() else None),
    }


@app.get("/api/presets")
def get_presets() -> dict:
    return {
        "tag_groups": presets.TAG_GROUPS,
        "structure_markers": presets.STRUCTURE_MARKERS,
        "examples": [
            {"id": e["id"], "title": e["title"], "tags": e["tags"]} for e in presets.EXAMPLES
        ],
    }


@app.get("/api/examples/{example_id}")
def get_example(example_id: str) -> dict:
    example = presets.load_example(example_id)
    if example is None:
        raise HTTPException(404, {"code": "error.example_not_found"})
    return example


@app.post("/api/tags/preview")
def preview_tags(body: TagPreviewRequest) -> dict:
    normalized = presets.normalize_tags(body.tags)
    return {"normalized": normalized, "count": len([t for t in normalized.split(",") if t])}


@app.post("/api/lyrics/check")
async def check_lyrics(request: Request) -> dict:
    body = await request.json()
    text = str(body.get("lyrics", ""))
    return {
        "warnings": presets.validate_lyrics(text),
        "characters": len(text),
        "estimated_tokens": engine.estimate_prompt_tokens("", text),
    }


# --------------------------------------------------------------------------
# Checkpoints
# --------------------------------------------------------------------------
@app.get("/api/checkpoints/plan")
def checkpoint_plan(source: str = "huggingface") -> dict:
    """Local state only — answers instantly even with no network."""
    config = get_config()
    state = checkpoints.describe(config)
    state["cli"] = checkpoints.cli_commands(config, source)
    return state


@app.get("/api/checkpoints/sizes")
def checkpoint_sizes() -> dict:
    """Download sizes from the hub. Split from /plan because it can be slow
    or unreachable, and the setup screen must not wait for it."""
    return {"sizes": checkpoints.remote_sizes()}


@app.post("/api/checkpoints/download")
def start_download(body: DownloadRequest) -> dict:
    queue = get_queue()
    if queue.active():
        raise HTTPException(409, {"code": "error.busy"})
    config = get_config()

    def run(job: Job) -> dict:
        def progress(fraction: float, message: str) -> None:
            if queue.cancelled(job):
                raise CancelledError()
            queue.update(job, stage="download", progress=fraction, message=message)

        return checkpoints.download(
            config,
            source=body.source,
            component_ids=body.components,
            progress=progress,
            should_cancel=lambda: queue.cancelled(job),
        )

    job = queue.submit("download", run, meta={"source": body.source})
    return job.snapshot()


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------
@app.post("/api/model/load")
def load_model(body: ModelLoadRequest) -> dict:
    queue = get_queue()
    if queue.active():
        raise HTTPException(409, {"code": "error.busy"})
    config = get_config()

    def run(job: Job) -> dict:
        queue.update(job, stage="load_model", progress=0.1, message="")
        engine.get_manager().get(
            config,
            version=body.version,
            mula_device=body.mula_device,
            codec_device=body.codec_device,
            mula_dtype=body.mula_dtype,
            codec_dtype=body.codec_dtype,
            lazy_load=body.lazy_load,
        )
        queue.update(job, stage="ready", progress=1.0)
        return engine.get_manager().describe()

    job = queue.submit("load_model", run)
    return job.snapshot()


@app.post("/api/model/unload")
def unload_model() -> dict:
    if get_queue().active():
        raise HTTPException(409, {"code": "error.busy"})
    engine.get_manager().unload()
    return {"ok": True}


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------
@app.post("/api/generate")
def generate(body: GenerateRequest) -> dict:
    config = get_config()
    queue = get_queue()

    if not engine.heartlib_installed() or not engine.torch_status()["installed"]:
        raise HTTPException(409, {"code": "error.heartlib_missing"})
    state = checkpoints.describe(config)
    if not state["ready"]:
        missing = [c["id"] for c in state["components"] if not c["present"]]
        raise HTTPException(409, {"code": "error.checkpoints_missing", "missing": missing})
    if queue.active():
        raise HTTPException(409, {"code": "error.busy"})

    if len(body.tags) > MAX_TAGS_CHARS:
        raise HTTPException(422, {"code": "error.tags_too_long", "max": MAX_TAGS_CHARS})
    if len(body.lyrics) > MAX_LYRICS_CHARS:
        raise HTTPException(422, {"code": "error.lyrics_too_long", "max": MAX_LYRICS_CHARS})
    if not body.lyrics.strip():
        raise HTTPException(422, {"code": "error.lyrics_empty"})

    tags = presets.normalize_tags(body.tags)
    if not tags:
        raise HTTPException(422, {"code": "error.tags_empty"})

    prompt_tokens = engine.estimate_prompt_tokens(tags, body.lyrics)
    ceiling = engine.max_duration_s(prompt_tokens)
    if body.duration_s > ceiling:
        raise HTTPException(
            422,
            {"code": "error.duration_exceeds_context", "max_duration_s": ceiling},
        )

    settings = {
        "version": config.version,
        "mula_device": config.mula_device,
        "codec_device": config.codec_device,
        "mula_dtype": config.mula_dtype,
        "codec_dtype": config.codec_dtype,
        "lazy_load": config.lazy_load,
    }

    def run(job: Job) -> dict:
        payload = body.model_dump()
        payload["tags"] = tags
        payload["job_id"] = job.id

        def on_stage(stage: str, progress: float, message: str) -> None:
            queue.update(job, stage=stage, progress=progress, message=message)

        try:
            return engine.generate(
                config,
                payload,
                settings,
                on_stage,
                should_cancel=lambda: queue.cancelled(job),
            )
        except JobCancelled as exc:
            raise CancelledError() from exc

    job = queue.submit("generate", run, meta={"title": body.title})
    return job.snapshot()


# --------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------
@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = get_queue().get(job_id)
    if job is None:
        raise HTTPException(404, {"code": "error.job_not_found"})
    return job.snapshot()


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict:
    if not get_queue().cancel(job_id):
        raise HTTPException(409, {"code": "error.job_not_cancellable"})
    return {"ok": True}


@app.get("/api/jobs/{job_id}/events")
def job_events(job_id: str) -> StreamingResponse:
    queue = get_queue()
    if queue.get(job_id) is None:
        raise HTTPException(404, {"code": "error.job_not_found"})

    def stream():
        seen = -1
        deadline = time.time() + 3 * 60 * 60
        while time.time() < deadline:
            job = queue.get(job_id)
            if job is None:
                break
            yield f"data: {json.dumps(job.snapshot())}\n\n"
            if job.state in {"done", "error", "cancelled"}:
                break
            seen = queue.wait_for_change(seen, timeout=2.0)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --------------------------------------------------------------------------
# History and audio
# --------------------------------------------------------------------------
@app.get("/api/history")
def history() -> dict:
    return {"entries": engine.read_history(get_config())}


@app.delete("/api/history/{entry_id}")
def delete_history(entry_id: str) -> dict:
    if not engine.delete_history_entry(get_config(), entry_id):
        raise HTTPException(404, {"code": "error.entry_not_found"})
    return {"ok": True}


@app.get("/api/audio/{entry_id}")
def audio(entry_id: str, download: bool = False) -> FileResponse:
    path = engine.audio_path(get_config(), entry_id)
    if path is None:
        raise HTTPException(404, {"code": "error.audio_not_found"})
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media_type,
        filename=path.name if download else None,
    )


# Mounted last so /api/* keeps priority. html=True serves index.html at "/".
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

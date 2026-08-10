"""A single-worker job queue.

The generation pipeline mutates shared KV caches via ``setup_caches``
(music_generation.py:283), so it is not safe to run two generations at once.
Serialising every job through one worker thread is a correctness requirement,
not a throttle.
"""

from __future__ import annotations

import queue
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

JobKind = Literal["generate", "download", "load_model"]
JobState = Literal["queued", "running", "done", "error", "cancelled"]


@dataclass
class Job:
    id: str
    kind: JobKind
    state: JobState = "queued"
    stage: str = "queued"
    progress: float = 0.0
    message: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    result: Any = None
    error: str | None = None
    meta: dict = field(default_factory=dict)
    _cancel: threading.Event = field(default_factory=threading.Event, repr=False)

    def snapshot(self) -> dict:
        elapsed = (self.finished_at or time.time()) - (self.started_at or self.created_at)
        eta = None
        if self.state == "running" and 0.02 < self.progress < 1.0:
            eta = max(0.0, elapsed / self.progress - elapsed)
        return {
            "id": self.id,
            "kind": self.kind,
            "state": self.state,
            "stage": self.stage,
            "progress": round(self.progress, 4),
            "message": self.message,
            "elapsed_s": round(elapsed, 1),
            "eta_s": round(eta, 1) if eta is not None else None,
            "result": self.result,
            "error": self.error,
            "meta": self.meta,
        }


class JobQueue:
    """Registry plus one worker thread."""

    def __init__(self, keep: int = 50) -> None:
        self._jobs: dict[str, Job] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()
        self._queue: queue.Queue[tuple[Job, Callable[[Job], Any]]] = queue.Queue()
        self._keep = keep
        self._version = 0
        self._changed = threading.Condition()
        self._worker = threading.Thread(target=self._run, name="studio-worker", daemon=True)
        self._worker.start()

    # -- public API -------------------------------------------------------
    def submit(self, kind: JobKind, fn: Callable[[Job], Any], meta: dict | None = None) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], kind=kind, meta=meta or {})
        with self._lock:
            self._jobs[job.id] = job
            self._order.append(job.id)
            self._prune()
        self._queue.put((job, fn))
        self._notify()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if job is None or job.state in {"done", "error", "cancelled"}:
            return False
        job._cancel.set()
        if job.state == "queued":
            job.state = "cancelled"
            job.stage = "cancelled"
            job.finished_at = time.time()
        self._notify()
        return True

    def active(self) -> Job | None:
        with self._lock:
            for job_id in reversed(self._order):
                job = self._jobs[job_id]
                if job.state in {"queued", "running"}:
                    return job
        return None

    def wait_for_change(self, seen: int, timeout: float) -> int:
        """Block until any job changes, so SSE does not have to busy-poll."""
        with self._changed:
            if self._version != seen:
                return self._version
            self._changed.wait(timeout)
            return self._version

    @property
    def version(self) -> int:
        return self._version

    # -- job-facing helpers ----------------------------------------------
    def update(
        self,
        job: Job,
        *,
        stage: str | None = None,
        progress: float | None = None,
        message: str | None = None,
    ) -> None:
        if stage is not None:
            job.stage = stage
        if progress is not None:
            job.progress = max(0.0, min(1.0, progress))
        if message is not None:
            job.message = message
        self._notify()

    @staticmethod
    def cancelled(job: Job) -> bool:
        return job._cancel.is_set()

    # -- internals --------------------------------------------------------
    def _notify(self) -> None:
        with self._changed:
            self._version += 1
            self._changed.notify_all()

    def _prune(self) -> None:
        while len(self._order) > self._keep:
            oldest = self._order[0]
            if self._jobs[oldest].state in {"queued", "running"}:
                break
            self._order.pop(0)
            self._jobs.pop(oldest, None)

    def _run(self) -> None:
        while True:
            job, fn = self._queue.get()
            if job._cancel.is_set():
                job.state = "cancelled"
                job.finished_at = time.time()
                self._notify()
                continue
            job.state = "running"
            job.started_at = time.time()
            job.stage = "starting"
            self._notify()
            try:
                job.result = fn(job)
                job.state = "cancelled" if job._cancel.is_set() else "done"
                job.stage = job.state
                job.progress = 1.0 if job.state == "done" else job.progress
            except CancelledError:
                job.state = "cancelled"
                job.stage = "cancelled"
            except Exception as exc:
                job.state = "error"
                job.stage = "error"
                job.error = f"{type(exc).__name__}: {exc}"
                traceback.print_exc()
            finally:
                job.finished_at = time.time()
                self._notify()


class CancelledError(RuntimeError):
    """Raised by a job body to report a cooperative abort."""


_queue: JobQueue | None = None


def get_queue() -> JobQueue:
    global _queue
    if _queue is None:
        _queue = JobQueue()
    return _queue

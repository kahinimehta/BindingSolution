"""In-process background jobs with progress reporting.

AI analyses and Zotero syncs can take a while, so write endpoints start a
job and return its id immediately; the frontend polls `GET /api/jobs/{id}`
to render live progress. Jobs run in daemon threads — fine for a
single-user localhost tool.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable

_registry: dict[str, "Job"] = {}
_lock = threading.Lock()
_MAX_FINISHED = 50  # keep memory bounded


class Job:
    def __init__(self, kind: str) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.status = "queued"  # queued | running | done | error
        self.progress: dict[str, Any] = {"current": 0, "total": 0, "message": ""}
        self.result: Any = None
        self.error: str | None = None
        self.created_at = time.time()
        self.finished_at: float | None = None

    def set_progress(self, current: int, total: int, message: str = "") -> None:
        self.progress = {"current": current, "total": total, "message": message}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
        }


def _prune() -> None:
    finished = [j for j in _registry.values() if j.finished_at is not None]
    if len(finished) <= _MAX_FINISHED:
        return
    finished.sort(key=lambda j: j.finished_at or 0)
    for job in finished[: len(finished) - _MAX_FINISHED]:
        _registry.pop(job.id, None)


def start(kind: str, fn: Callable[[Job], Any]) -> Job:
    """Run `fn(job)` in a background thread; its return value becomes job.result."""
    job = Job(kind)
    with _lock:
        _registry[job.id] = job
        _prune()

    def _runner() -> None:
        job.status = "running"
        try:
            job.result = fn(job)
            job.status = "done"
        except Exception as exc:  # surfaced to the UI via job.error
            job.error = str(exc) or exc.__class__.__name__
            job.status = "error"
        finally:
            job.finished_at = time.time()

    threading.Thread(target=_runner, name=f"job-{kind}-{job.id}", daemon=True).start()
    return job


def get(job_id: str) -> Job | None:
    with _lock:
        return _registry.get(job_id)

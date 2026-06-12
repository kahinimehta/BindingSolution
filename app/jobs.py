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


class JobCancelled(Exception):
    """Raised when a cooperative cancel is requested for a running job."""


class Job:
    def __init__(self, kind: str) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.status = "queued"  # queued | running | done | error | cancelled
        self.progress: dict[str, Any] = {
            "current": 0, "total": 0, "message": "", "indeterminate": False,
        }
        self.result: Any = None
        self.error: str | None = None
        self.created_at = time.time()
        self.finished_at: float | None = None
        self._cancel = threading.Event()

    def request_cancel(self) -> bool:
        """Request cooperative cancellation. Returns False if already finished."""
        if self.status in ("done", "error", "cancelled"):
            return False
        self._cancel.set()
        return True

    def check_cancelled(self) -> None:
        if self._cancel.is_set():
            raise JobCancelled("Cancelled")

    def set_progress(
        self,
        current: int,
        total: int,
        message: str = "",
        *,
        indeterminate: bool = False,
    ) -> None:
        self.check_cancelled()
        self.progress = {
            "current": current,
            "total": total,
            "message": message,
            "indeterminate": indeterminate,
        }

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


def _finalize_done_progress(job: Job) -> None:
    """Ensure finished jobs never leave an indeterminate bar as the last state."""
    p = job.progress
    total = max(int(p.get("total") or 0), int(p.get("current") or 0), 1)
    message = (p.get("message") or "").strip() or "Done"
    if message not in ("Done", "Up to date"):
        message = "Done"
    job.set_progress(total, total, message, indeterminate=False)


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
            _finalize_done_progress(job)
            job.status = "done"
        except JobCancelled:
            job.error = "Cancelled"
            job.status = "cancelled"
            job.progress = {
                **job.progress,
                "message": "Cancelled",
                "indeterminate": False,
            }
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


def cancel(job_id: str) -> bool:
    """Request cooperative cancellation for a queued or running job."""
    with _lock:
        job = _registry.get(job_id)
        if job is None:
            return False
        return job.request_cancel()


def reset_registry() -> None:
    """Clear in-memory jobs (tests only)."""
    with _lock:
        _registry.clear()


def list_jobs(*, active_only: bool = False) -> list[Job]:
    """Return jobs newest-first. With active_only, only queued/running."""
    with _lock:
        jobs = list(_registry.values())
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    if active_only:
        jobs = [j for j in jobs if j.status in ("queued", "running")]
    return jobs

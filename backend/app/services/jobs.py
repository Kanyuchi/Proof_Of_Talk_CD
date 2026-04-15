"""
Simple in-memory job tracker for long-running dashboard operations.

Railway's HTTP edge closes requests after ~30s, but individual worker
processes stay alive for minutes. This lets us fire long jobs (Grid
re-enrichment, sponsor intelligence reports, match regeneration) as
asyncio tasks and return a 202 immediately — the frontend polls
GET /dashboard/jobs/{job_id} for status + result.

This is deliberately dumb (single-process, lost on restart). Good enough
for admin-only operations that take < 5 minutes. If we need durability
or multi-worker, swap for Redis-backed RQ/Arq later.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

# job_id -> state dict
_JOBS: dict[str, dict[str, Any]] = {}

# Auto-expire completed jobs older than this many seconds
_TTL_SECONDS = 3600


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cleanup_expired() -> None:
    """Drop jobs that finished more than TTL seconds ago."""
    now = datetime.now(timezone.utc)
    expired = []
    for jid, job in _JOBS.items():
        finished = job.get("finished_at")
        if not finished:
            continue
        try:
            age = (now - datetime.fromisoformat(finished)).total_seconds()
            if age > _TTL_SECONDS:
                expired.append(jid)
        except (ValueError, TypeError):
            pass
    for jid in expired:
        _JOBS.pop(jid, None)


def submit(
    kind: str,
    coro_factory: Callable[[], Coroutine[Any, Any, Any]],
    metadata: dict | None = None,
) -> str:
    """Submit a background job. Returns the new job_id.

    `coro_factory` is a zero-arg callable that returns a fresh coroutine
    each time — passed as a factory (not a coroutine directly) so we can
    schedule it on the running event loop cleanly.
    """
    _cleanup_expired()
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {
        "id": job_id,
        "kind": kind,
        "status": "pending",
        "created_at": _now(),
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
        "metadata": metadata or {},
    }

    async def _runner() -> None:
        _JOBS[job_id]["status"] = "running"
        _JOBS[job_id]["started_at"] = _now()
        try:
            result = await coro_factory()
            _JOBS[job_id]["result"] = result
            _JOBS[job_id]["status"] = "done"
        except Exception as exc:  # noqa: BLE001
            _JOBS[job_id]["error"] = f"{type(exc).__name__}: {exc}"
            _JOBS[job_id]["status"] = "error"
        finally:
            _JOBS[job_id]["finished_at"] = _now()

    asyncio.create_task(_runner())
    return job_id


def get(job_id: str) -> dict | None:
    return _JOBS.get(job_id)


def list_recent(limit: int = 20) -> list[dict]:
    _cleanup_expired()
    return sorted(
        _JOBS.values(),
        key=lambda j: j.get("created_at", ""),
        reverse=True,
    )[:limit]

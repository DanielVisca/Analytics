import asyncio
import time
import uuid
from typing import Any, Optional

from app.config import settings
from app.db import get_clickhouse
from app.insights import run_funnel, run_trend

# In-memory job store (v1). Replace with Redis/Celery for production.
_jobs: dict[str, dict[str, Any]] = {}
_lock = asyncio.Lock()


def _cleanup_old() -> None:
    now = time.monotonic()
    to_del = [jid for jid, j in _jobs.items() if (now - j.get("_created", 0)) > settings.async_job_ttl_seconds]
    for jid in to_del:
        _jobs.pop(jid, None)


async def create_and_run_job(project_id: str, query_type: str, params: dict[str, Any]) -> str:
    job_id = str(uuid.uuid4())
    async with _lock:
        _cleanup_old()
        _jobs[job_id] = {"status": "pending", "result": None, "_created": time.monotonic()}
    asyncio.create_task(_run_job(job_id, project_id, query_type, params))
    return job_id


async def _run_job(job_id: str, project_id: str, query_type: str, params: dict[str, Any]) -> None:
    try:
        client = get_clickhouse()
        if query_type == "trend":
            result = run_trend(
                client,
                project_id=project_id,
                event=params.get("event", ""),
                date_from=params.get("date_from"),
                date_to=params.get("date_to"),
                interval=params.get("interval", "day"),
            )
        elif query_type == "funnel":
            result = run_funnel(
                client,
                project_id=project_id,
                steps=params.get("steps", []),
                date_from=params.get("date_from"),
                date_to=params.get("date_to"),
            )
        else:
            result = {"error": "unknown type"}
        async with _lock:
            if job_id in _jobs:
                _jobs[job_id]["status"] = "completed"
                _jobs[job_id]["result"] = result
    except Exception as e:
        async with _lock:
            if job_id in _jobs:
                _jobs[job_id]["status"] = "failed"
                _jobs[job_id]["result"] = {"error": str(e)}


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    _cleanup_old()
    return _jobs.get(job_id)

import asyncio
import json
import uuid
from typing import Any, Optional

import redis

from app.config import settings
from app.db import get_clickhouse
from app.insights import run_funnel, run_trend

_redis: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _job_key(job_id: str) -> str:
    return f"async_job:{job_id}"


async def create_and_run_job(project_id: str, query_type: str, params: dict[str, Any]) -> str:
    job_id = str(uuid.uuid4())
    r = _get_redis()
    payload = {"status": "pending", "result": None}
    r.setex(
        _job_key(job_id),
        settings.async_job_ttl_seconds,
        json.dumps(payload),
    )
    asyncio.create_task(_run_job(job_id, project_id, query_type, params))
    return job_id


async def _run_job(job_id: str, project_id: str, query_type: str, params: dict[str, Any]) -> None:
    r = _get_redis()
    key = _job_key(job_id)
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
                strict=params.get("strict", True),
                conversion_window_days=min(max(1, int(params.get("conversion_window_days", 30))), 365),
            )
        else:
            result = {"error": "unknown type"}
        payload = {"status": "completed", "result": result}
        r.setex(key, settings.async_job_ttl_seconds, json.dumps(payload))
    except Exception as e:
        payload = {"status": "failed", "result": {"error": str(e)}}
        r.setex(key, settings.async_job_ttl_seconds, json.dumps(payload))


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    r = _get_redis()
    raw = r.get(_job_key(job_id))
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        return {"status": data.get("status", "pending"), "result": data.get("result")}
    except (json.JSONDecodeError, TypeError):
        return None

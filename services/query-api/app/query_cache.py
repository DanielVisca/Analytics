"""Redis-backed cache for trend and funnel query results."""
import hashlib
import json
from typing import Any, Optional

import redis

from app.config import settings

_redis: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _cache_key(project_id: str, query_type: str, params: dict[str, Any]) -> str:
    payload = {"project_id": project_id, "type": query_type, "params": params}
    key_str = json.dumps(payload, sort_keys=True, default=str)
    h = hashlib.sha256(key_str.encode()).hexdigest()
    return f"query_cache:{h}"


def get_cached(project_id: str, query_type: str, params: dict[str, Any]) -> Optional[dict[str, Any]]:
    r = _get_redis()
    key = _cache_key(project_id, query_type, params)
    raw = r.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def set_cached(
    project_id: str,
    query_type: str,
    params: dict[str, Any],
    result: dict[str, Any],
) -> None:
    r = _get_redis()
    key = _cache_key(project_id, query_type, params)
    r.setex(
        key,
        settings.query_cache_ttl_seconds,
        json.dumps(result, default=str),
    )

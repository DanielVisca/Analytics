"""In-memory rate limiter (fixed window per minute)."""
import time
from typing import Any

# key -> (count_this_minute, minute_ts)
_limits: dict[str, tuple[int, int]] = {}
_limit_lock: Any = None


def _get_lock() -> Any:
    global _limit_lock
    if _limit_lock is None:
        import threading
        _limit_lock = threading.Lock()
    return _limit_lock


def check_rate_limit(key: str, limit_per_minute: int) -> tuple[bool, int]:
    """Returns (allowed, retry_after_seconds). retry_after_seconds is 0 if allowed."""
    if limit_per_minute <= 0:
        return True, 0
    now = time.time()
    minute_ts = int(now // 60)
    with _get_lock():
        if key not in _limits:
            _limits[key] = (1, minute_ts)
            return True, 0
        count, window_min = _limits[key]
        if minute_ts > window_min:
            count, window_min = 0, minute_ts
        count += 1
        _limits[key] = (count, window_min)
        if count > limit_per_minute:
            # Retry after the current minute ends
            retry_after = int(60 - (now % 60)) + 1
            return False, min(retry_after, 60)
    return True, 0

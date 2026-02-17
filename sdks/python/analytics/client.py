import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx


class Analytics:
    """Server-side SDK: same event shape, sync or async HTTP with batching and retries."""

    def __init__(
        self,
        host: str,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        batch_size: int = 10,
        flush_interval_seconds: float = 5.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.0,
    ):
        self.host = host.rstrip("/")
        self.api_key = api_key
        self.project_id = project_id
        self.batch_size = batch_size
        self.flush_interval = flush_interval_seconds
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff_seconds
        self._queue: list[dict[str, Any]] = []
        self._last_flush = 0.0

    def capture(
        self,
        event: str,
        properties: Optional[dict[str, Any]] = None,
        distinct_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        payload: dict[str, Any] = {
            "event": event,
            "distinct_id": distinct_id or str(uuid.uuid4()),
            "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
            "properties": properties or {},
            "uuid": str(uuid.uuid4()),
            "$lib": "python",
            "$lib_version": "1.0.0",
        }
        if self.project_id:
            payload["project_id"] = self.project_id
        self._queue.append(payload)
        self._maybe_flush()

    def _maybe_flush(self) -> None:
        now = time.monotonic()
        if len(self._queue) >= self.batch_size or (
            self._queue and (now - self._last_flush) >= self.flush_interval
        ):
            self.flush()

    def flush(self) -> None:
        if not self._queue:
            return
        batch = self._queue[: self.batch_size]
        del self._queue[: len(batch)]
        self._last_flush = time.monotonic()
        body: dict[str, Any] = (
            {"batch": batch, "project_id": self.project_id}
            if len(batch) > 1
            else {**batch[0]}
        )
        self._send(body)

    def _send(self, body: dict[str, Any], retry: int = 0) -> None:
        url = f"{self.host}/capture"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=10.0) as client:
                    r = client.post(url, json=body, headers=headers)
                if r.status_code in (200, 202):
                    return
                raise RuntimeError(f"Capture failed: {r.status_code} {r.text}")
            except Exception as e:
                if attempt == self.max_retries:
                    raise
                time.sleep(self.retry_backoff * (attempt + 1))

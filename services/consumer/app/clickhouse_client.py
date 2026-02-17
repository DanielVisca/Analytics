from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import clickhouse_connect
from clickhouse_connect.driver import Client

from app.config import settings


def get_client() -> Client:
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_database,
    )


def _parse_ts(ts: Any) -> Optional[datetime]:
    if ts is None or ts == "":
        return None
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def row_from_event(raw: dict[str, Any]) -> tuple:
    """Build a row tuple for analytics.events (timestamp, uuid, event, distinct_id, project_id, properties, lib, lib_version, device_id)."""
    ts = _parse_ts(raw.get("timestamp")) or datetime.utcnow()
    uuid_val = raw.get("uuid")
    if uuid_val is not None and uuid_val != "":
        try:
            uuid_val = UUID(str(uuid_val))
        except (ValueError, TypeError):
            uuid_val = None
    else:
        uuid_val = None
    event = str(raw.get("event", ""))[:4096]
    distinct_id = str(raw.get("distinct_id", ""))[:4096]
    project_id = str(raw.get("project_id") or "default")[:256]
    import json
    properties = json.dumps(raw.get("properties") or {})
    lib = (raw.get("$lib") or raw.get("lib")) and str((raw.get("$lib") or raw.get("lib")))[:128]
    lib_version = (raw.get("$lib_version") or raw.get("lib_version")) and str((raw.get("$lib_version") or raw.get("lib_version")))[:64]
    device_id = (raw.get("$device_id") or raw.get("device_id")) and str((raw.get("$device_id") or raw.get("device_id")))[:256]
    return (ts, uuid_val, event, distinct_id, project_id, properties, lib, lib_version, device_id)


def insert_batch(client: Client, rows: list[tuple]) -> None:
    if not rows:
        return
    client.insert(
        settings.clickhouse_table,
        rows,
        column_names=[
            "timestamp",
            "uuid",
            "event",
            "distinct_id",
            "project_id",
            "properties",
            "lib",
            "lib_version",
            "device_id",
        ],
    )

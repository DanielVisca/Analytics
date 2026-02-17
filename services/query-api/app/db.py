"""ClickHouse client with connection reuse (single client per process)."""
from contextlib import asynccontextmanager
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver import Client

from app.config import settings

_clickhouse_client: Client | None = None


def init_clickhouse_pool() -> None:
    global _clickhouse_client
    _clickhouse_client = clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_database,
    )


def get_clickhouse() -> Client:
    """Return the shared ClickHouse client (initialized in lifespan)."""
    if _clickhouse_client is None:
        init_clickhouse_pool()
    return _clickhouse_client  # type: ignore


def close_clickhouse_pool() -> None:
    global _clickhouse_client
    if _clickhouse_client is not None:
        try:
            _clickhouse_client.close()
        except Exception:
            pass
        _clickhouse_client = None

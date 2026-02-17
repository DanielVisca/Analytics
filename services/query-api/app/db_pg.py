"""PostgreSQL connection pool."""
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from app.config import settings

_pool: pool.ThreadedConnectionPool | None = None


class PooledConnection:
    """Wrapper that returns a connection to the pool on close()."""

    def __init__(self, conn, connection_pool: pool.ThreadedConnectionPool):
        self._conn = conn
        self._pool = connection_pool

    def cursor(self, *args, **kwargs):
        return self._conn.cursor(cursor_factory=RealDictCursor, *args, **kwargs)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        if self._conn is not None:
            self._pool.putconn(self._conn)
            self._conn = None


def init_pg_pool() -> None:
    global _pool
    _pool = pool.ThreadedConnectionPool(
        minconn=settings.postgres_pool_min,
        maxconn=settings.postgres_pool_max,
        dsn=settings.postgres_dsn,
    )


def get_pg_conn() -> PooledConnection:
    if _pool is None:
        init_pg_pool()
    conn = _pool.getconn()
    return PooledConnection(conn, _pool)


def close_pg_pool() -> None:
    global _pool
    if _pool is not None:
        try:
            _pool.closeall()
        except Exception:
            pass
        _pool = None

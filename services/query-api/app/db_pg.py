import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import settings


def get_pg_conn():
    return psycopg2.connect(settings.postgres_dsn, cursor_factory=RealDictCursor)

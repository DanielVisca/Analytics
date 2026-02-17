import clickhouse_connect
from clickhouse_connect.driver import Client

from app.config import settings


def get_clickhouse() -> Client:
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_database,
    )

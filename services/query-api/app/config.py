from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 18123
    clickhouse_database: str = "analytics"
    postgres_dsn: str = "postgresql://analytics:analytics@localhost:5432/analytics"
    # For async job storage (v1 in-memory; can switch to Redis)
    async_job_ttl_seconds: int = 3600

    class Config:
        env_prefix = "QUERY_"


settings = Settings()

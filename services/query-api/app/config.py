from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 18123
    clickhouse_database: str = "analytics"
    postgres_dsn: str = "postgresql://analytics:analytics@localhost:5432/analytics"
    async_job_ttl_seconds: int = 3600
    require_api_key: bool = False
    auth_api_url: str = "http://localhost:8002"
    clickhouse_pool_size: int = 4
    postgres_pool_min: int = 2
    postgres_pool_max: int = 10
    redis_url: str = "redis://localhost:6379/0"
    query_cache_ttl_seconds: int = 120

    class Config:
        env_prefix = "QUERY_"


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "events"
    kafka_group_id: str = "event-consumers"
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 18123
    clickhouse_database: str = "analytics"
    clickhouse_table: str = "events"
    batch_size: int = 1000
    batch_interval_seconds: float = 5.0
    metrics_port: int = 9090
    insert_retry_count: int = 3
    insert_retry_backoff_seconds: float = 1.0
    dlq_topic: str = "events-dlq"
    shutdown_wait_seconds: float = 30.0

    class Config:
        env_prefix = "CONSUMER_"


settings = Settings()

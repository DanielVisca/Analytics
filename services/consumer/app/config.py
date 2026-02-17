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

    class Config:
        env_prefix = "CONSUMER_"


settings = Settings()

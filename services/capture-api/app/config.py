from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "events"
    # Optional: require X-API-Key and resolve project_id
    require_api_key: bool = False

    class Config:
        env_prefix = "CAPTURE_"


settings = Settings()

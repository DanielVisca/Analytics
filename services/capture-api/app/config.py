from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "events"
    require_api_key: bool = False
    auth_api_url: str = "http://localhost:8002"
    max_request_body_bytes: int = 512 * 1024  # 512 KB
    properties_max_keys: int = 50
    properties_max_depth: int = 3
    properties_max_size_bytes: int = 32 * 1024  # 32 KB
    kafka_send_timeout_seconds: float = 5.0
    rate_limit_requests_per_minute: int = 0  # 0 = disabled
    rate_limit_key_header: str = "X-API-Key"  # or X-Forwarded-For for IP

    class Config:
        env_prefix = "CAPTURE_"


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_dsn: str = "postgresql://analytics:analytics@localhost:5432/analytics"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 86400 * 7  # 7 days

    class Config:
        env_prefix = "AUTH_"


settings = Settings()

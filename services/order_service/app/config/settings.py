"""Order Service configuration settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "order-service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/order_service_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Downstream Services
    PRODUCT_SERVICE_URL: str = "http://localhost:8002"

    # JWT
    JWT_SECRET: str = "super_secret_jwt_key_for_development_purposes_min32chars"
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

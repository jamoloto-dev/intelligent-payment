"""API Gateway configuration settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "api-gateway"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Gateway Port
    PORT: int = 8000

    # Downstream Microservice URLs
    USER_SERVICE_URL: str = "http://localhost:8001"
    PRODUCT_SERVICE_URL: str = "http://localhost:8002"
    ORDER_SERVICE_URL: str = "http://localhost:8003"
    FRAUD_SERVICE_URL: str = "http://localhost:8004"
    PAYMENT_SERVICE_URL: str = "http://localhost:8005"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8006"

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 120

    # JWT
    JWT_SECRET: str = "super_secret_jwt_key_for_development_purposes_min32chars"
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

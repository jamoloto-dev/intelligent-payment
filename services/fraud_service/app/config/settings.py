"""Fraud Service configuration settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "fraud-service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Thresholds
    HIGH_AMOUNT_THRESHOLD: float = 1000.0
    CRITICAL_AMOUNT_THRESHOLD: float = 5000.0
    MAX_VELOCITY_TX_PER_HOUR: int = 5
    MAX_FAILED_ATTEMPTS: int = 3

    # Storage & Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "fraud_detection_db"

    # JWT
    JWT_SECRET: str = "super_secret_jwt_key_for_development_purposes_min32chars"
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

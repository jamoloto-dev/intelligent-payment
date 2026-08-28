"""Payment Service configuration settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "payment-service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/payment_service_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Downstream Services
    FRAUD_SERVICE_URL: str = "http://localhost:8004"
    ORDER_SERVICE_URL: str = "http://localhost:8003"

    # Payment Provider (Stripe)
    STRIPE_SECRET_KEY: str = "sk_test_placeholder_key"
    STRIPE_WEBHOOK_SECRET: str = "whsec_placeholder_secret"
    USE_MOCK_PAYMENT_PROVIDER: bool = True

    # JWT
    JWT_SECRET: str = "super_secret_jwt_key_for_development_purposes_min32chars"
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

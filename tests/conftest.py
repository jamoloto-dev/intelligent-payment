"""Pytest global fixtures and cleanup."""
import asyncio
import os
import pytest
from shared.database.base import Base

import services.user_service.app.main as user_main
import services.product_service.app.main as product_main
import services.order_service.app.main as order_main
import services.fraud_service.app.main as fraud_main
import services.payment_service.app.main as payment_main
import services.notification_service.app.main as notif_main
import services.api_gateway.app.main as gateway_main

os.environ["JWT_SECRET"] = "super_secret_jwt_key_for_development_purposes_min32chars"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["USE_MOCK_PAYMENT_PROVIDER"] = "true"


@pytest.fixture(autouse=True)
def cleanup_overrides():
    """Ensure clean dependency overrides per test."""
    yield
    for mod in [user_main, product_main, order_main, fraud_main, payment_main, notif_main, gateway_main]:
        mod.app.dependency_overrides.clear()

"""Pytest global fixtures and cleanup."""

import os

import pytest

import services.api_gateway.app.main as gateway_main
import services.fraud_service.app.main as fraud_main
import services.notification_service.app.main as notif_main
import services.order_service.app.main as order_main
import services.payment_service.app.main as payment_main
import services.product_service.app.main as product_main
import services.user_service.app.main as user_main

os.environ["JWT_SECRET"] = "super_secret_jwt_key_for_development_purposes_min32chars"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["USE_MOCK_PAYMENT_PROVIDER"] = "true"


def restore_default_overrides():
    user_main.app.dependency_overrides[user_main.get_user_service] = (
        user_main.get_user_service_dependency
    )
    product_main.app.dependency_overrides[product_main.get_product_service] = (
        product_main.get_product_service_dependency
    )
    order_main.app.dependency_overrides[order_main.get_order_service] = (
        order_main.get_order_service_dependency
    )
    fraud_main.app.dependency_overrides[fraud_main.get_fraud_service] = (
        fraud_main.get_fraud_service_dependency
    )
    payment_main.app.dependency_overrides[payment_main.get_payment_service] = (
        payment_main.get_payment_service_dependency
    )
    notif_main.app.dependency_overrides[notif_main.get_notification_service] = (
        notif_main.get_notification_service_dependency
    )


@pytest.fixture(autouse=True)
def cleanup_overrides():
    """Ensure clean dependency overrides per test while preserving service defaults."""
    restore_default_overrides()
    yield
    for mod in [
        user_main,
        product_main,
        order_main,
        fraud_main,
        payment_main,
        notif_main,
        gateway_main,
    ]:
        mod.app.dependency_overrides.clear()
    restore_default_overrides()

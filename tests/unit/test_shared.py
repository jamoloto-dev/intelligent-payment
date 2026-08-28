"""Unit tests for shared library modules."""

import asyncio
from datetime import timedelta

import pytest

from shared.authentication.jwt import JWTManager
from shared.authentication.password import hash_password, verify_password
from shared.azure.keyvault import SecretProvider
from shared.azure.tables import AuditTableStorage
from shared.events.redis_client import EventBus
from shared.logging.logger import sanitize_data
from shared.schemas.events import OrderCreatedEvent, OrderItemPayload


def test_password_hashing_and_verification():
    plain = "SuperSecurePassword123!"
    hashed = hash_password(plain)

    assert hashed != plain
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password("", hashed) is False


def test_jwt_manager_flow():
    secret = "a_very_secret_test_key_for_jwt_manager_testing_32bytes"
    jwt_mgr = JWTManager(secret_key=secret, algorithm="HS256", access_token_expire_minutes=15)

    token = jwt_mgr.create_access_token(
        user_id="usr_12345",
        email="test@example.com",
        role="ADMIN",
    )
    assert isinstance(token, str)

    payload = jwt_mgr.decode_token(token)
    assert payload.sub == "usr_12345"
    assert payload.email == "test@example.com"
    assert payload.role == "ADMIN"


def test_jwt_expired_token():
    secret = "a_very_secret_test_key_for_jwt_manager_testing_32bytes"
    jwt_mgr = JWTManager(secret_key=secret, algorithm="HS256", access_token_expire_minutes=-10)

    token = jwt_mgr.create_access_token(
        user_id="usr_12345",
        email="test@example.com",
        role="USER",
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(ValueError, match="expired"):
        jwt_mgr.decode_token(token)


def test_sensitive_data_sanitization():
    raw_payload = {
        "username": "alice",
        "password": "SuperSecretPassword!",
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "stripe_secret_key": "sk_test_1234567890",
        "profile": {"credit_card": "4111-2222-3333-4444", "country": "US"},
        "items": [{"product_id": "prod_1", "card_number": "1234"}],
    }

    sanitized = sanitize_data(raw_payload)
    assert sanitized["username"] == "alice"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"
    assert sanitized["stripe_secret_key"] == "[REDACTED]"
    assert sanitized["profile"]["credit_card"] == "[REDACTED]"
    assert sanitized["profile"]["country"] == "US"
    assert sanitized["items"][0]["card_number"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_event_bus_in_memory_fallback():
    bus = EventBus(redis_url="redis://nonexistent:9999/0")
    await bus.connect()

    received_events = []

    async def sample_handler(event_data):
        received_events.append(event_data)

    bus.subscribe("OrderCreated", sample_handler)

    sample_order_event = OrderCreatedEvent(
        order_id="ord_999",
        user_id="usr_888",
        total_amount=150.00,
        currency="USD",
        items=[
            OrderItemPayload(product_id="prod_1", quantity=2, unit_price=75.00, subtotal=150.00)
        ],
    )

    await bus.publish("orders_channel", sample_order_event)
    await asyncio.sleep(0.05)

    assert len(received_events) == 1
    assert received_events[0]["order_id"] == "ord_999"
    assert received_events[0]["event_type"] == "OrderCreated"

    await bus.disconnect()


@pytest.mark.asyncio
async def test_azure_tables_fallback():
    audit_storage = AuditTableStorage(table_name="TestAudit")
    res = await audit_storage.log_audit_event(
        partition_key="payment_tests",
        event_type="PaymentCompleted",
        payload={"payment_id": "pay_1", "amount": 100.0},
    )

    assert res["PartitionKey"] == "payment_tests"
    assert res["EventType"] == "PaymentCompleted"

    records = audit_storage.get_audit_records(partition_key="payment_tests")
    assert len(records) >= 1
    assert records[0]["EventType"] == "PaymentCompleted"


def test_azure_keyvault_env_fallback(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    provider = SecretProvider()
    secret = provider.get_secret("DATABASE_URL")
    assert secret == "postgresql://user:pass@localhost:5432/db"

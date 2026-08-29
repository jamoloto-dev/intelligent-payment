"""Tests for concurrent idempotency requests and race condition handling."""

import asyncio
import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.payment_service.app.config.settings import settings
from services.payment_service.app.main import app
from services.payment_service.app.providers.mock_provider import MockPaymentProvider
from services.payment_service.app.repositories.payment_repository import PaymentRepository
from services.payment_service.app.routers.payment_router import get_payment_service
from services.payment_service.app.services.payment_service import PaymentService
from shared.authentication.jwt import JWTManager
from shared.database.base import Base

DB_FILE = f"/tmp/test_payment_concurrent_{uuid.uuid4().hex[:8]}.db"

test_engine = create_async_engine(
    f"sqlite+aiosqlite:///{DB_FILE}?timeout=30",
    echo=False,
)
TestingSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


class MockApprovedFraudClient:
    async def check(self, *args, **kwargs):
        return {"decision": "APPROVE", "risk_score": 10.0, "reasons": []}


mock_provider = MockPaymentProvider()
mock_fraud = MockApprovedFraudClient()


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_payment_service():
        async with TestingSessionLocal() as session:
            yield PaymentService(
                repository=PaymentRepository(session),
                provider=mock_provider,
                fraud_client=mock_fraud,
            )

    app.dependency_overrides[get_payment_service] = override_get_payment_service
    yield
    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except OSError:
            pass


jwt_mgr = JWTManager(secret_key=settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
user_token = jwt_mgr.create_access_token(
    user_id="usr_concurrent_1", email="concurrent@example.com", role="USER"
)


@pytest.mark.asyncio
async def test_simultaneous_idempotency_requests():
    """Test that two simultaneous requests with the same idempotency key don't double charge."""
    transport = ASGITransport(app=app)
    shared_idempotency_key = f"idemp_concurrent_tx_{uuid.uuid4().hex[:8]}"

    async def send_payment_request():
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            return await ac.post(
                "/payments",
                json={
                    "order_id": "ord_concurrent_1",
                    "amount": 199.99,
                    "currency": "USD",
                    "payment_method_id": "pm_card_visa",
                    "idempotency_key": shared_idempotency_key,
                },
                headers={"Authorization": f"Bearer {user_token}"},
            )

    # Launch two simultaneous requests concurrently
    res1, res2 = await asyncio.gather(send_payment_request(), send_payment_request())

    assert res1.status_code == 201
    assert res2.status_code == 201

    data1 = res1.json()
    data2 = res2.json()

    # Both requests must return the exact same payment record
    assert data1["id"] == data2["id"]
    assert data1["order_id"] == "ord_concurrent_1"
    assert data2["order_id"] == "ord_concurrent_1"
    assert data1["status"] == "SUCCEEDED"
    assert data2["status"] == "SUCCEEDED"

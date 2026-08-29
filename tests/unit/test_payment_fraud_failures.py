"""Tests verifying safe failure handling when fraud evaluation is degraded, times out, or returns malformed payloads."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from services.payment_service.app.config.settings import settings
from services.payment_service.app.main import app
from services.payment_service.app.providers.mock_provider import MockPaymentProvider
from services.payment_service.app.repositories.payment_repository import PaymentRepository
from services.payment_service.app.routers.payment_router import get_payment_service
from services.payment_service.app.services.payment_service import PaymentService
from shared.authentication.jwt import JWTManager
from shared.database.base import Base

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestingSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


class TimeoutFraudClient:
    async def check(self, *args, **kwargs):
        raise TimeoutError("Connection to fraud service timed out after 5000ms")


class MalformedFraudClient:
    async def check(self, *args, **kwargs):
        return {"garbage": "payload_with_no_decision"}


class InternalErrorFraudClient:
    async def check(self, *args, **kwargs):
        raise RuntimeError("Internal database crash in fraud microservice")


mock_provider = MockPaymentProvider()


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


jwt_mgr = JWTManager(secret_key=settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
user_token = jwt_mgr.create_access_token(
    user_id="usr_fraud_safe", email="safe@example.com", role="USER"
)


@pytest.mark.asyncio
async def test_fraud_service_timeout_fails_safely():
    """Verify timeout does not auto-approve, but flags for REVIEW safely."""

    async def override_get_payment_service():
        async with TestingSessionLocal() as session:
            yield PaymentService(
                repository=PaymentRepository(session),
                provider=mock_provider,
                fraud_client=TimeoutFraudClient(),
            )

    app.dependency_overrides[get_payment_service] = override_get_payment_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/payments",
            json={
                "order_id": "ord_timeout_1",
                "amount": 150.00,
                "currency": "USD",
                "payment_method_id": "pm_card_visa",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 400
        data = res.json()
        assert data["error"] == "PAYMENT_UNDER_REVIEW"
        assert "review" in data["message"].lower()


@pytest.mark.asyncio
async def test_fraud_service_malformed_response_fails_safely():
    """Verify malformed JSON without decision field defaults to REVIEW."""

    async def override_get_payment_service():
        async with TestingSessionLocal() as session:
            yield PaymentService(
                repository=PaymentRepository(session),
                provider=mock_provider,
                fraud_client=MalformedFraudClient(),
            )

    app.dependency_overrides[get_payment_service] = override_get_payment_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/payments",
            json={
                "order_id": "ord_malformed_1",
                "amount": 75.00,
                "currency": "USD",
                "payment_method_id": "pm_card_visa",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 400
        data = res.json()
        assert data["error"] == "PAYMENT_UNDER_REVIEW"


@pytest.mark.asyncio
async def test_fraud_service_crash_fails_safely():
    """Verify backend exception in fraud service defaults to REVIEW."""

    async def override_get_payment_service():
        async with TestingSessionLocal() as session:
            yield PaymentService(
                repository=PaymentRepository(session),
                provider=mock_provider,
                fraud_client=InternalErrorFraudClient(),
            )

    app.dependency_overrides[get_payment_service] = override_get_payment_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/payments",
            json={
                "order_id": "ord_crash_1",
                "amount": 500.00,
                "currency": "USD",
                "payment_method_id": "pm_card_visa",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 400
        data = res.json()
        assert data["error"] == "PAYMENT_UNDER_REVIEW"

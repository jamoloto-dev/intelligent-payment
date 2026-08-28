"""Unit and API tests for Payment Service."""

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


class MockFraudClient:
    """Mock fraud service for payment testing."""

    async def check(
        self,
        transaction_id,
        order_id,
        user_id,
        amount,
        currency,
        billing_country=None,
        client_ip=None,
    ):
        if amount > 5000:
            return {"decision": "REJECT", "risk_score": 90.0, "reasons": ["Unusually large amount"]}
        return {"decision": "APPROVE", "risk_score": 5.0, "reasons": []}


mock_provider = MockPaymentProvider()
mock_fraud = MockFraudClient()


@pytest.fixture(autouse=True)
async def setup_test_db():
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


jwt_mgr = JWTManager(secret_key=settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
user_token = jwt_mgr.create_access_token(user_id="usr_pay_1", email="pay@example.com", role="USER")


@pytest.mark.asyncio
async def test_payment_successful_charge():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/payments",
            json={
                "order_id": "ord_101",
                "amount": 250.00,
                "currency": "USD",
                "payment_method_id": "pm_card_visa",
                "idempotency_key": "idemp_key_101",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["order_id"] == "ord_101"
        assert float(data["amount"]) == 250.00
        assert data["status"] == "SUCCEEDED"
        assert data["provider_transaction_id"].startswith("ch_mock_succ")

        # Verify idempotency: calling again with same idempotency_key returns identical record
        res_idemp = await ac.post(
            "/payments",
            json={
                "order_id": "ord_101",
                "amount": 250.00,
                "currency": "USD",
                "idempotency_key": "idemp_key_101",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res_idemp.status_code == 201
        assert res_idemp.json()["id"] == data["id"]


@pytest.mark.asyncio
async def test_payment_fraud_rejection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Amount > 5000 triggers fraud rejection in mock fraud client
        res = await ac.post(
            "/payments",
            json={
                "order_id": "ord_fraud_1",
                "amount": 7500.00,
                "currency": "USD",
                "payment_method_id": "pm_card_visa",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 400
        assert res.json()["error"] == "PAYMENT_FRAUD_REJECTED"


@pytest.mark.asyncio
async def test_payment_refund():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        charge_res = await ac.post(
            "/payments",
            json={"order_id": "ord_ref_1", "amount": 80.00, "currency": "USD"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        pay_id = charge_res.json()["id"]

        refund_res = await ac.post(
            f"/payments/{pay_id}/refund",
            json={"amount": 80.00, "reason": "Defective item"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert refund_res.status_code == 200
        assert refund_res.json()["status"] == "REFUNDED"

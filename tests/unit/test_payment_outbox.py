"""Tests for the Transactional Outbox Pattern and background outbox worker."""

import json
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from services.payment_service.app.events.outbox_processor import OutboxProcessor
from services.payment_service.app.providers.mock_provider import MockPaymentProvider
from services.payment_service.app.repositories.payment_repository import PaymentRepository
from services.payment_service.app.schemas.payment import PaymentCreateRequest
from services.payment_service.app.services.payment_service import PaymentService
from shared.database.base import Base

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestingSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


class MockApprovedFraudClient:
    async def check(self, *args, **kwargs):
        return {"decision": "APPROVE", "risk_score": 10.0, "reasons": []}


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_payment_persists_outbox_when_redis_offline():
    """Verify payment succeeds and outbox message is stored even if Redis event bus fails."""
    # Mock EventBus that raises an error when publishing
    failing_event_bus = AsyncMock()
    failing_event_bus.publish.side_effect = ConnectionError("Redis connection refused")

    mock_provider = MockPaymentProvider()
    mock_fraud = MockApprovedFraudClient()

    async with TestingSessionLocal() as session:
        repo = PaymentRepository(session)
        service = PaymentService(
            repository=repo,
            provider=mock_provider,
            event_bus=failing_event_bus,
            fraud_client=mock_fraud,
        )

        req = PaymentCreateRequest(
            order_id="ord_outbox_1",
            amount=Decimal("120.00"),
            currency="USD",
            payment_method_id="pm_card_visa",
            idempotency_key="idemp_outbox_001",
        )

        # Payment should still succeed despite Redis failure
        res = await service.process_payment(user_id="usr_outbox_1", req=req)
        assert res.status_code if hasattr(res, "status_code") else res.status == "SUCCEEDED"

    # Now verify the outbox table contains the PENDING message
    async with TestingSessionLocal() as session:
        repo = PaymentRepository(session)
        pending = await repo.get_pending_outbox_messages()
        assert len(pending) == 1
        assert pending[0].event_type == "PaymentCompletedEvent"
        assert pending[0].status == "PENDING"
        payload = json.loads(pending[0].payload)
        assert payload["order_id"] == "ord_outbox_1"
        assert float(payload["amount"]) == 120.00


@pytest.mark.asyncio
async def test_outbox_processor_dispatches_pending_messages():
    """Verify OutboxProcessor successfully publishes pending messages and marks them PUBLISHED."""
    # Setup test event bus that succeeds
    successful_event_bus = AsyncMock()

    # Pre-populate a pending outbox message
    async with TestingSessionLocal() as session:
        repo = PaymentRepository(session)
        repo.add_outbox_event(
            topic="payments",
            event_type="PaymentCompletedEvent",
            payload={"order_id": "ord_outbox_2", "amount": 350.00, "status": "SUCCEEDED"},
        )
        await session.commit()

    # Run OutboxProcessor batch
    processor = OutboxProcessor(
        session_factory=TestingSessionLocal,
        event_bus=successful_event_bus,
    )
    count = await processor.process_batch()
    assert count == 1
    assert successful_event_bus.publish.called

    # Verify message is now PUBLISHED
    async with TestingSessionLocal() as session:
        repo = PaymentRepository(session)
        pending = await repo.get_pending_outbox_messages()
        assert len(pending) == 0

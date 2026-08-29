"""Payment repository for database access and transactional outbox."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.payment_service.app.models.outbox import OutboxMessage
from services.payment_service.app.models.payment import Payment


class PaymentRepository:
    """Encapsulates payment database operations and outbox messages."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, payment_id: str) -> Payment | None:
        result = await self.session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def get_by_user_idempotency(self, user_id: str, idempotency_key: str) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(
                and_(Payment.user_id == user_id, Payment.idempotency_key == idempotency_key)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: str) -> list[Payment]:
        result = await self.session.execute(select(Payment).where(Payment.order_id == order_id))
        return list(result.scalars().all())

    async def create(self, payment: Payment) -> Payment:
        self.session.add(payment)
        await self.session.commit()
        try:
            await self.session.refresh(payment)
        except Exception:
            pass
        return payment

    async def update(self, payment: Payment) -> Payment:
        await self.session.commit()
        try:
            await self.session.refresh(payment)
        except Exception:
            pass
        return payment

    def add_outbox_event(
        self, topic: str, event_type: str, payload: dict[str, Any] | str
    ) -> OutboxMessage:
        """Add an outbox event to the current transaction."""
        payload_str = (
            json.dumps(payload, default=str) if isinstance(payload, dict) else str(payload)
        )
        outbox_msg = OutboxMessage(
            topic=topic,
            event_type=event_type,
            payload=payload_str,
            status="PENDING",
            retry_count=0,
        )
        self.session.add(outbox_msg)
        return outbox_msg

    async def save_payment_with_outbox(
        self,
        payment: Payment,
        topic: str | None = None,
        event_type: str | None = None,
        payload: dict[str, Any] | str | None = None,
    ) -> Payment:
        """Atomically persist payment record and outbox event in the same transaction."""
        self.session.add(payment)
        if topic and event_type and payload is not None:
            self.add_outbox_event(topic, event_type, payload)
        await self.session.commit()
        try:
            await self.session.refresh(payment)
        except Exception:
            pass
        return payment

    async def update_payment_with_outbox(
        self,
        payment: Payment,
        topic: str | None = None,
        event_type: str | None = None,
        payload: dict[str, Any] | str | None = None,
    ) -> Payment:
        """Atomically update payment record and insert outbox event in the same transaction."""
        if topic and event_type and payload is not None:
            self.add_outbox_event(topic, event_type, payload)
        await self.session.commit()
        try:
            await self.session.refresh(payment)
        except Exception:
            pass
        return payment

    async def get_pending_outbox_messages(self, limit: int = 50) -> list[OutboxMessage]:
        stmt = (
            select(OutboxMessage)
            .where(OutboxMessage.status == "PENDING")
            .order_by(OutboxMessage.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_outbox_published(self, message_id: str) -> None:
        await self.session.execute(
            update(OutboxMessage)
            .where(OutboxMessage.id == message_id)
            .values(status="PUBLISHED", processed_at=datetime.now(UTC))
        )
        await self.session.commit()

    async def mark_outbox_failed(self, message_id: str, error: str) -> None:
        await self.session.execute(
            update(OutboxMessage)
            .where(OutboxMessage.id == message_id)
            .values(
                status="FAILED",
                error_message=error[:1000],
                retry_count=OutboxMessage.retry_count + 1,
            )
        )
        await self.session.commit()

    async def list_payments(
        self,
        user_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Payment], int]:
        filters = []
        if user_id:
            filters.append(Payment.user_id == user_id)

        count_stmt = select(func.count(Payment.id)).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            select(Payment)
            .where(*filters)
            .order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

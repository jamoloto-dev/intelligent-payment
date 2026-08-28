"""Payment repository for database access."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.payment_service.app.models.payment import Payment


class PaymentRepository:
    """Encapsulates payment database operations."""

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

    async def get_by_order_id(self, order_id: str) -> list[Payment]:
        result = await self.session.execute(select(Payment).where(Payment.order_id == order_id))
        return list(result.scalars().all())

    async def create(self, payment: Payment) -> Payment:
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def update(self, payment: Payment) -> Payment:
        await self.session.commit()
        await self.session.refresh(payment)
        return payment

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

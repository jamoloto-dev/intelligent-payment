"""Order repository for database access."""
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from services.order_service.app.models.order import Order, OrderItem


class OrderRepository:
    """Encapsulates order and order-item database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, order_id: str) -> Optional[Order]:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def update(self, order: Order) -> Order:
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def delete(self, order: Order) -> None:
        await self.session.delete(order)
        await self.session.commit()

    async def list_orders(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Order], int]:
        filters = []
        if user_id:
            filters.append(Order.user_id == user_id)
        if status:
            filters.append(Order.status == status)

        count_stmt = select(func.count(Order.id)).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            select(Order)
            .where(*filters)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

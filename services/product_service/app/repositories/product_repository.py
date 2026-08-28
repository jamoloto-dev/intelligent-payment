"""Product repository for database access."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.product_service.app.models.product import Product


class ProductRepository:
    """Encapsulates product catalog and inventory database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, product_id: str, for_update: bool = False) -> Product | None:
        stmt = select(Product).where(Product.id == product_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def update(self, product: Product) -> Product:
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def delete(self, product: Product) -> None:
        await self.session.delete(product)
        await self.session.commit()

    async def list_products(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        only_active: bool = True,
    ) -> tuple[list[Product], int]:
        filters = []
        if only_active:
            filters.append(Product.is_active == True)
        if search:
            filters.append(Product.name.ilike(f"%{search}%"))

        count_stmt = select(func.count(Product.id)).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            select(Product)
            .where(*filters)
            .order_by(Product.name.asc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

"""Product service business logic layer."""
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from shared.logging.logger import get_logger
from services.product_service.app.models.product import Product
from services.product_service.app.repositories.product_repository import ProductRepository
from services.product_service.app.schemas.product import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
    StockReservationRequest,
    StockReservationResponse,
)

logger = get_logger("product-service")


class ProductService:
    """Handles product catalog and atomic inventory operations."""

    def __init__(self, repository: ProductRepository):
        self.repository = repository

    async def create_product(self, req: ProductCreateRequest) -> ProductResponse:
        product = Product(
            name=req.name,
            description=req.description or "",
            price=req.price,
            currency=req.currency.upper(),
            stock_quantity=req.stock_quantity,
        )
        created = await self.repository.create(product)
        logger.info(f"Created product: {created.id} - {created.name}")
        return ProductResponse.model_validate(created)

    async def get_product(self, product_id: str) -> ProductResponse:
        product = await self.repository.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "PRODUCT_NOT_FOUND", "message": f"Product {product_id} not found"},
            )
        return ProductResponse.model_validate(product)

    async def update_product(self, product_id: str, req: ProductUpdateRequest) -> ProductResponse:
        product = await self.repository.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "PRODUCT_NOT_FOUND", "message": f"Product {product_id} not found"},
            )

        if req.name is not None:
            product.name = req.name
        if req.description is not None:
            product.description = req.description
        if req.price is not None:
            product.price = req.price
        if req.currency is not None:
            product.currency = req.currency.upper()
        if req.stock_quantity is not None:
            product.stock_quantity = req.stock_quantity
        if req.is_active is not None:
            product.is_active = req.is_active

        updated = await self.repository.update(product)
        logger.info(f"Updated product {product_id}")
        return ProductResponse.model_validate(updated)

    async def delete_product(self, product_id: str) -> None:
        product = await self.repository.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "PRODUCT_NOT_FOUND", "message": f"Product {product_id} not found"},
            )
        await self.repository.delete(product)
        logger.info(f"Deleted product {product_id}")

    async def list_products(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        only_active: bool = True,
    ) -> Tuple[List[ProductResponse], int]:
        products, total = await self.repository.list_products(
            page=page, page_size=page_size, search=search, only_active=only_active
        )
        return [ProductResponse.model_validate(p) for p in products], total

    async def reserve_stock(self, product_id: str, req: StockReservationRequest) -> StockReservationResponse:
        """Atomically decrement stock for order placement."""
        product = await self.repository.get_by_id(product_id, for_update=True)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "PRODUCT_NOT_FOUND", "message": f"Product {product_id} not found"},
            )

        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "PRODUCT_INACTIVE", "message": f"Product {product.name} is no longer active"},
            )

        if product.stock_quantity < req.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INSUFFICIENT_STOCK",
                    "message": f"Insufficient stock for {product.name}. Available: {product.stock_quantity}, Requested: {req.quantity}",
                },
            )

        product.stock_quantity -= req.quantity
        await self.repository.update(product)
        logger.info(f"Reserved {req.quantity} units of {product.name} (remaining: {product.stock_quantity})")
        return StockReservationResponse(
            product_id=product.id,
            reserved_quantity=req.quantity,
            remaining_stock=product.stock_quantity,
            unit_price=product.price,
            currency=product.currency,
        )

    async def release_stock(self, product_id: str, req: StockReservationRequest) -> StockReservationResponse:
        """Atomically increment stock when order is cancelled or payment fails."""
        product = await self.repository.get_by_id(product_id, for_update=True)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "PRODUCT_NOT_FOUND", "message": f"Product {product_id} not found"},
            )

        product.stock_quantity += req.quantity
        await self.repository.update(product)
        logger.info(f"Released {req.quantity} units of {product.name} (new stock: {product.stock_quantity})")
        return StockReservationResponse(
            product_id=product.id,
            reserved_quantity=req.quantity,
            remaining_stock=product.stock_quantity,
            unit_price=product.price,
            currency=product.currency,
        )

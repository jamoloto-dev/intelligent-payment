"""Product service API endpoints protected with Granular RBAC."""

from fastapi import APIRouter, Depends, Query, status

from services.product_service.app.schemas.product import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
    StockReservationRequest,
    StockReservationResponse,
)
from services.product_service.app.services.product_service import ProductService
from shared.authentication.dependencies import require_permission
from shared.authentication.jwt import TokenPayload
from shared.schemas.common import PaginatedResponse

product_router = APIRouter(prefix="/products", tags=["Products"])


def get_product_service() -> ProductService:
    # Overridden in main.py
    pass


@product_router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    req: ProductCreateRequest,
    current_user: TokenPayload = Depends(require_permission("products:create")),
    service: ProductService = Depends(get_product_service),
):
    """Create a new product (Operations / Admin)."""
    return await service.create_product(req)


@product_router.get("", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    only_active: bool = Query(True),
    service: ProductService = Depends(get_product_service),
):
    """List products with pagination and search (Public / Storefront)."""
    items, total = await service.list_products(
        page=page, page_size=page_size, search=search, only_active=only_active
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@product_router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    service: ProductService = Depends(get_product_service),
):
    """Get single product details."""
    return await service.get_product(product_id)


@product_router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    req: ProductUpdateRequest,
    current_user: TokenPayload = Depends(require_permission("products:update")),
    service: ProductService = Depends(get_product_service),
):
    """Update product details or inventory (Operations / Admin)."""
    return await service.update_product(product_id, req)


@product_router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: TokenPayload = Depends(require_permission("products:update")),
    service: ProductService = Depends(get_product_service),
):
    """Delete a product (Admin only)."""
    await service.delete_product(product_id)


@product_router.post("/{product_id}/reserve", response_model=StockReservationResponse)
async def reserve_product_stock(
    product_id: str,
    req: StockReservationRequest,
    service: ProductService = Depends(get_product_service),
):
    """Atomically reserve inventory for an order (Internal/Service)."""
    return await service.reserve_stock(product_id, req)


@product_router.post("/{product_id}/release", response_model=StockReservationResponse)
async def release_product_stock(
    product_id: str,
    req: StockReservationRequest,
    service: ProductService = Depends(get_product_service),
):
    """Atomically release reserved inventory (Internal/Service)."""
    return await service.release_stock(product_id, req)

"""Order service API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.order_service.app.schemas.order import (
    OrderCreateRequest,
    OrderResponse,
    OrderStatusUpdateRequest,
    OrderUpdateRequest,
)
from services.order_service.app.services.order_service import OrderService
from shared.authentication.dependencies import (
    require_authenticated,
)
from shared.authentication.jwt import TokenPayload
from shared.schemas.common import PaginatedResponse, UserRole

order_router = APIRouter(prefix="/orders", tags=["Orders"])


def get_order_service() -> OrderService:
    # Overridden in main.py
    pass


@order_router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    req: OrderCreateRequest,
    current_user: TokenPayload = Depends(require_authenticated),
    service: OrderService = Depends(get_order_service),
):
    """Create a new order and reserve product inventory."""
    return await service.create_order(
        user_id=current_user.sub,
        user_email=current_user.email,
        req=req,
    )


@order_router.get("", response_model=PaginatedResponse[OrderResponse])
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    current_user: TokenPayload = Depends(require_authenticated),
    service: OrderService = Depends(get_order_service),
):
    """List orders for current user, or all orders for Admin."""
    user_id = None if current_user.role == UserRole.ADMIN.value else current_user.sub
    items, total = await service.list_orders(
        user_id=user_id, status_filter=status_filter, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@order_router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: TokenPayload = Depends(require_authenticated),
    service: OrderService = Depends(get_order_service),
):
    """Get order details by ID."""
    order = await service.get_order(order_id)
    if current_user.role != UserRole.ADMIN.value and order.user_id != current_user.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Access denied to this order"},
        )
    return order


@order_router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str,
    req: OrderUpdateRequest,
    current_user: TokenPayload = Depends(require_authenticated),
    service: OrderService = Depends(get_order_service),
):
    """Update order details."""
    order = await service.get_order(order_id)
    if current_user.role != UserRole.ADMIN.value and order.user_id != current_user.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Access denied to modify this order"},
        )
    return await service.update_order(order_id, req)


@order_router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    current_user: TokenPayload = Depends(require_authenticated),
    service: OrderService = Depends(get_order_service),
):
    """Cancel an active order and release inventory."""
    is_admin = current_user.role == UserRole.ADMIN.value
    return await service.cancel_order(
        order_id=order_id, user_id=current_user.sub, is_admin=is_admin
    )


@order_router.post("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    req: OrderStatusUpdateRequest,
    service: OrderService = Depends(get_order_service),
):
    """Internal service webhook to update order status upon payment events."""
    return await service.update_status(order_id, req.status, req.reason)

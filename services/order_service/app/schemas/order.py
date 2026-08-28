"""Order request and response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from shared.schemas.common import BaseResponse, OrderStatus


class OrderItemCreateRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0, description="Quantity must be at least 1")


class OrderCreateRequest(BaseModel):
    items: list[OrderItemCreateRequest] = Field(
        ..., min_length=1, description="Order must contain at least 1 item"
    )
    shipping_address: str = Field(..., min_length=5, description="Valid delivery address")
    currency: str | None = Field(default="USD", min_length=3, max_length=3)


class OrderUpdateRequest(BaseModel):
    shipping_address: str | None = Field(None, min_length=5)
    status: OrderStatus | None = None


class OrderItemResponse(BaseResponse):
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderResponse(BaseResponse):
    id: str
    user_id: str
    status: str
    total_amount: Decimal
    currency: str
    shipping_address: str
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus
    reason: str | None = None

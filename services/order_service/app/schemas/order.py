"""Order request and response schemas."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
from shared.schemas.common import BaseResponse, OrderStatus


class OrderItemCreateRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0, description="Quantity must be at least 1")


class OrderCreateRequest(BaseModel):
    items: List[OrderItemCreateRequest] = Field(..., min_length=1, description="Order must contain at least 1 item")
    shipping_address: str = Field(..., min_length=5, description="Valid delivery address")
    currency: Optional[str] = Field(default="USD", min_length=3, max_length=3)


class OrderUpdateRequest(BaseModel):
    shipping_address: Optional[str] = Field(None, min_length=5)
    status: Optional[OrderStatus] = None


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
    items: List[OrderItemResponse] = []


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus
    reason: Optional[str] = None

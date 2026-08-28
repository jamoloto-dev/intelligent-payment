"""Product request and response schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
from shared.schemas.common import BaseResponse


class ProductCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default="")
    price: Decimal = Field(..., gt=0, description="Product price must be greater than zero")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    stock_quantity: int = Field(default=0, ge=0, description="Stock quantity cannot be negative")


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    stock_quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductResponse(BaseResponse):
    id: str
    name: str
    description: str
    price: Decimal
    currency: str
    stock_quantity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StockReservationRequest(BaseModel):
    quantity: int = Field(..., gt=0, description="Number of items to reserve")


class StockReservationResponse(BaseModel):
    product_id: str
    reserved_quantity: int
    remaining_stock: int
    unit_price: Decimal
    currency: str

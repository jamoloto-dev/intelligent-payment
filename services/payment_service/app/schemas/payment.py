"""Payment request and response schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from shared.schemas.common import BaseResponse, PaymentStatus


class PaymentCreateRequest(BaseModel):
    order_id: str
    amount: Decimal = Field(..., gt=0, description="Amount to charge")
    currency: Optional[str] = Field(default="USD", min_length=3, max_length=3)
    payment_method_id: Optional[str] = Field(default="pm_card_visa", description="Stripe PaymentMethod token or mock token")
    idempotency_key: Optional[str] = Field(None, description="Unique client key preventing double charging")
    user_email: Optional[str] = None
    client_ip: Optional[str] = None
    billing_country: Optional[str] = None


class PaymentRefundRequest(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0, description="Optional partial refund amount")
    reason: Optional[str] = Field(default="Customer requested refund")


class PaymentResponse(BaseResponse):
    id: str
    order_id: str
    user_id: str
    amount: Decimal
    currency: str
    provider: str
    provider_transaction_id: Optional[str] = None
    status: str
    idempotency_key: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StripeWebhookPayload(BaseModel):
    id: str
    type: str
    data: Dict[str, Any]

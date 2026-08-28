"""Payment request and response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from shared.schemas.common import BaseResponse


class PaymentCreateRequest(BaseModel):
    order_id: str
    amount: Decimal = Field(..., gt=0, description="Amount to charge")
    currency: str | None = Field(default="USD", min_length=3, max_length=3)
    payment_method_id: str | None = Field(
        default="pm_card_visa", description="Stripe PaymentMethod token or mock token"
    )
    idempotency_key: str | None = Field(
        None, description="Unique client key preventing double charging"
    )
    user_email: str | None = None
    client_ip: str | None = None
    billing_country: str | None = None


class PaymentRefundRequest(BaseModel):
    amount: Decimal | None = Field(None, gt=0, description="Optional partial refund amount")
    reason: str | None = Field(default="Customer requested refund")


class PaymentResponse(BaseResponse):
    id: str
    order_id: str
    user_id: str
    amount: Decimal
    currency: str
    provider: str
    provider_transaction_id: str | None = None
    status: str
    idempotency_key: str | None = None
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class StripeWebhookPayload(BaseModel):
    id: str
    type: str
    data: dict[str, Any]

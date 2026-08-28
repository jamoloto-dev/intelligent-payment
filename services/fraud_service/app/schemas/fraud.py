"""Fraud detection schemas."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from shared.schemas.common import BaseResponse, FraudDecision, FraudRiskLevel


class FraudCheckRequest(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction or payment reference ID")
    order_id: str
    user_id: str
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD")
    account_created_at: datetime | None = None
    user_email: str | None = None
    client_ip: str | None = None
    device_id: str | None = None
    payment_method: str | None = "card"
    recent_transactions_count_1h: int | None = 0
    recent_failed_payments_24h: int | None = 0
    billing_country: str | None = None
    ip_country: str | None = None


class FraudCheckResponse(BaseResponse):
    transaction_id: str
    order_id: str
    user_id: str
    risk_score: float = Field(
        ..., ge=0.0, le=100.0, description="Risk score from 0 (clean) to 100 (critical fraud)"
    )
    risk_level: FraudRiskLevel
    decision: FraudDecision
    reasons: list[str]
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    rules_triggered: list[str] = []
    metadata: dict[str, Any] = {}

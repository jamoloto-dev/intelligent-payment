"""Fraud detection schemas."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from shared.schemas.common import BaseResponse, FraudDecision, FraudRiskLevel


class FraudCheckRequest(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction or payment reference ID")
    order_id: str
    user_id: str
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD")
    account_created_at: Optional[datetime] = None
    user_email: Optional[str] = None
    client_ip: Optional[str] = None
    device_id: Optional[str] = None
    payment_method: Optional[str] = "card"
    recent_transactions_count_1h: Optional[int] = 0
    recent_failed_payments_24h: Optional[int] = 0
    billing_country: Optional[str] = None
    ip_country: Optional[str] = None


class FraudCheckResponse(BaseResponse):
    transaction_id: str
    order_id: str
    user_id: str
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Risk score from 0 (clean) to 100 (critical fraud)")
    risk_level: FraudRiskLevel
    decision: FraudDecision
    reasons: List[str]
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    rules_triggered: List[str] = []
    metadata: Dict[str, Any] = {}

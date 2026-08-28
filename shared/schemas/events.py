"""Event schemas for asynchronous message passing."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base event payload structure."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_service: str = Field(default="system")
    correlation_id: Optional[str] = None


class OrderItemPayload(BaseModel):
    product_id: str
    product_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderCreatedEvent(BaseEvent):
    event_type: str = "OrderCreated"
    source_service: str = "order-service"
    order_id: str
    user_id: str
    total_amount: Decimal
    currency: str
    items: List[OrderItemPayload]
    user_email: Optional[str] = None


class OrderCancelledEvent(BaseEvent):
    event_type: str = "OrderCancelled"
    source_service: str = "order-service"
    order_id: str
    user_id: str
    reason: Optional[str] = None


class PaymentCreatedEvent(BaseEvent):
    event_type: str = "PaymentCreated"
    source_service: str = "payment-service"
    payment_id: str
    order_id: str
    user_id: str
    amount: Decimal
    currency: str
    provider: str


class PaymentCompletedEvent(BaseEvent):
    event_type: str = "PaymentCompleted"
    source_service: str = "payment-service"
    payment_id: str
    order_id: str
    user_id: str
    amount: Decimal
    currency: str
    provider: str
    provider_transaction_id: str
    user_email: Optional[str] = None


class PaymentFailedEvent(BaseEvent):
    event_type: str = "PaymentFailed"
    source_service: str = "payment-service"
    payment_id: str
    order_id: str
    user_id: str
    amount: Decimal
    currency: str
    provider: str
    reason: str
    user_email: Optional[str] = None


class PaymentRefundedEvent(BaseEvent):
    event_type: str = "PaymentRefunded"
    source_service: str = "payment-service"
    payment_id: str
    order_id: str
    user_id: str
    amount: Decimal
    currency: str
    provider: str
    refund_id: str
    user_email: Optional[str] = None


class FraudReviewRequiredEvent(BaseEvent):
    event_type: str = "FraudReviewRequired"
    source_service: str = "fraud-service"
    transaction_id: str
    order_id: str
    user_id: str
    risk_score: float
    risk_level: str
    decision: str
    reasons: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)

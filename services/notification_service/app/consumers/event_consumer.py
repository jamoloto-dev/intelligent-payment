"""Event consumer subscribing to domain events and generating notifications."""

from typing import Any

from services.notification_service.app.schemas.notification import (
    NotificationSendRequest,
    NotificationType,
)
from services.notification_service.app.services.notification_service import NotificationService
from shared.events.redis_client import EventBus
from shared.logging.logger import get_logger

logger = get_logger("notification-consumer")


class NotificationEventConsumer:
    """Listens to platform events (orders, payments, fraud) and dispatches notifications."""

    def __init__(self, event_bus: EventBus, notification_service: NotificationService):
        self.event_bus = event_bus
        self.service = notification_service

    def register_handlers(self):
        self.event_bus.subscribe("OrderCreated", self.handle_order_created)
        self.event_bus.subscribe("PaymentCompleted", self.handle_payment_completed)
        self.event_bus.subscribe("PaymentFailed", self.handle_payment_failed)
        self.event_bus.subscribe("PaymentRefunded", self.handle_payment_refunded)
        self.event_bus.subscribe("FraudReviewRequired", self.handle_fraud_alert)

    async def handle_order_created(self, event: dict[str, Any]):
        recipient = event.get("user_email") or f"user_{event.get('user_id')}@customer.local"
        order_id = event.get("order_id")
        total = event.get("total_amount")
        currency = event.get("currency", "USD")

        req = NotificationSendRequest(
            recipient=recipient,
            subject=f"Order Confirmed: #{order_id}",
            body=f"Thank you for your order #{order_id}! Total amount: {total} {currency}.",
            notification_type=NotificationType.LOG,
            event_type="OrderCreated",
            metadata={"order_id": order_id, "user_id": event.get("user_id")},
        )
        await self.service.send_notification(req)

    async def handle_payment_completed(self, event: dict[str, Any]):
        recipient = event.get("user_email") or f"user_{event.get('user_id')}@customer.local"
        payment_id = event.get("payment_id")
        amount = event.get("amount")
        currency = event.get("currency", "USD")

        req = NotificationSendRequest(
            recipient=recipient,
            subject=f"Payment Receipt: {amount} {currency}",
            body=f"We have received your payment of {amount} {currency} for order #{event.get('order_id')}.",
            notification_type=NotificationType.LOG,
            event_type="PaymentCompleted",
            metadata={"payment_id": payment_id, "order_id": event.get("order_id")},
        )
        await self.service.send_notification(req)

    async def handle_payment_failed(self, event: dict[str, Any]):
        recipient = event.get("user_email") or f"user_{event.get('user_id')}@customer.local"
        req = NotificationSendRequest(
            recipient=recipient,
            subject="Payment Failed",
            body=f"Your payment attempt for order #{event.get('order_id')} could not be processed. Reason: {event.get('reason')}",
            notification_type=NotificationType.LOG,
            event_type="PaymentFailed",
            metadata={"order_id": event.get("order_id")},
        )
        await self.service.send_notification(req)

    async def handle_payment_refunded(self, event: dict[str, Any]):
        recipient = event.get("user_email") or f"user_{event.get('user_id')}@customer.local"
        amount = event.get("amount")
        currency = event.get("currency", "USD")
        req = NotificationSendRequest(
            recipient=recipient,
            subject=f"Refund Processed: {amount} {currency}",
            body=f"Your refund of {amount} {currency} for order #{event.get('order_id')} has been processed.",
            notification_type=NotificationType.LOG,
            event_type="PaymentRefunded",
            metadata={"payment_id": event.get("payment_id")},
        )
        await self.service.send_notification(req)

    async def handle_fraud_alert(self, event: dict[str, Any]):
        req = NotificationSendRequest(
            recipient="security-alerts@intelligentpayment.com",
            subject=f"[SECURITY ALERT] Fraud Review Required - Score: {event.get('risk_score')}",
            body=f"Transaction {event.get('transaction_id')} for order {event.get('order_id')} was flagged for {event.get('decision')}. Reasons: {', '.join(event.get('reasons', []))}",
            notification_type=NotificationType.LOG,
            event_type="FraudReviewRequired",
            metadata=event,
        )
        await self.service.send_notification(req)

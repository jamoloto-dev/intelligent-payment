"""Stripe payment gateway integration."""

from decimal import Decimal
from typing import Any

import stripe

from services.payment_service.app.config.settings import settings
from services.payment_service.app.providers.base import (
    PaymentProviderInterface,
    ProviderChargeResult,
    ProviderRefundResult,
)
from shared.logging.logger import get_logger

logger = get_logger("stripe-provider")


class StripePaymentProvider(PaymentProviderInterface):
    """Integrates with Stripe API using Python SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        webhook_secret: str | None = None,
    ):
        self.api_key = api_key or settings.STRIPE_SECRET_KEY
        self.webhook_secret = webhook_secret or settings.STRIPE_WEBHOOK_SECRET
        stripe.api_key = self.api_key

    async def create_charge(
        self,
        amount: Decimal,
        currency: str,
        payment_method_id: str,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderChargeResult:
        try:
            # Stripe amounts are in cents
            amount_cents = int(amount * 100)

            # Create and confirm PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                payment_method=payment_method_id,
                confirm=True,
                automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
                idempotency_key=idempotency_key,
                metadata=metadata or {},
            )

            success = intent.status == "succeeded"
            return ProviderChargeResult(
                success=success,
                transaction_id=intent.id,
                amount=amount,
                currency=currency.upper(),
                status="SUCCEEDED" if success else intent.status.upper(),
                raw_response={"stripe_status": intent.status},
            )
        except stripe.StripeError as e:
            logger.error(f"Stripe API error: {e.user_message or str(e)}")
            return ProviderChargeResult(
                success=False,
                transaction_id="",
                amount=amount,
                currency=currency,
                status="FAILED",
                error_message=e.user_message or str(e),
                raw_response={"code": getattr(e, "code", "stripe_error")},
            )

    async def retrieve_charge(self, transaction_id: str) -> ProviderChargeResult:
        try:
            intent = stripe.PaymentIntent.retrieve(transaction_id)
            amount = Decimal(str(intent.amount / 100.0))
            return ProviderChargeResult(
                success=intent.status == "succeeded",
                transaction_id=intent.id,
                amount=amount,
                currency=intent.currency.upper(),
                status=intent.status.upper(),
                raw_response={"stripe_status": intent.status},
            )
        except stripe.StripeError as e:
            return ProviderChargeResult(
                success=False,
                transaction_id=transaction_id,
                amount=Decimal("0.00"),
                currency="USD",
                status="FAILED",
                error_message=str(e),
            )

    async def refund_charge(
        self,
        transaction_id: str,
        amount: Decimal | None = None,
        reason: str | None = None,
    ) -> ProviderRefundResult:
        try:
            amount_cents = int(amount * 100) if amount else None
            refund = stripe.Refund.create(
                payment_intent=transaction_id,
                amount=amount_cents,
                reason="requested_by_customer",
            )
            refund_amount = Decimal(str(refund.amount / 100.0))
            return ProviderRefundResult(
                success=refund.status == "succeeded",
                refund_id=refund.id,
                amount=refund_amount,
                status="SUCCEEDED" if refund.status == "succeeded" else refund.status.upper(),
            )
        except stripe.StripeError as e:
            logger.error(f"Stripe refund error: {e}")
            return ProviderRefundResult(
                success=False,
                refund_id="",
                amount=amount or Decimal("0.00"),
                status="FAILED",
                error_message=e.user_message or str(e),
            )

    def verify_webhook(self, payload: bytes, signature_header: str) -> dict[str, Any]:
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature_header,
                secret=self.webhook_secret,
            )
            return event
        except Exception as e:
            logger.error(f"Invalid Stripe webhook signature: {e}")
            raise ValueError(f"Invalid webhook signature: {e}")

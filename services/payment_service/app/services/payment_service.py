"""Payment Service business logic layer with transactional outbox and safe failure handling."""

import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from services.payment_service.app.config.settings import settings
from services.payment_service.app.models.payment import Payment
from services.payment_service.app.providers.base import PaymentProviderInterface
from services.payment_service.app.repositories.payment_repository import PaymentRepository
from services.payment_service.app.schemas.payment import (
    PaymentCreateRequest,
    PaymentRefundRequest,
    PaymentResponse,
)
from shared.events.redis_client import EventBus
from shared.logging.logger import get_logger
from shared.schemas.common import FraudDecision, PaymentStatus
from shared.schemas.events import (
    PaymentCompletedEvent,
    PaymentFailedEvent,
    PaymentRefundedEvent,
)

logger = get_logger("payment-service")


class PaymentService:
    """Orchestrates fraud evaluation, provider execution, idempotency, and lifecycle events."""

    def __init__(
        self,
        repository: PaymentRepository,
        provider: PaymentProviderInterface,
        event_bus: EventBus | None = None,
        fraud_client: Any | None = None,
    ):
        self.repository = repository
        self.provider = provider
        self.event_bus = event_bus
        self.fraud_client = fraud_client

    def _to_response(self, p: Payment) -> PaymentResponse:
        return PaymentResponse(
            id=str(p.id),
            order_id=str(p.order_id),
            user_id=str(p.user_id),
            amount=p.amount,
            currency=str(p.currency),
            provider=str(p.provider),
            provider_transaction_id=p.provider_transaction_id,
            status=p.status if isinstance(p.status, str) else p.status.value,
            idempotency_key=p.idempotency_key,
            failure_reason=p.failure_reason,
            created_at=p.created_at or datetime.now(UTC),
            updated_at=p.updated_at or datetime.now(UTC),
        )

    async def _check_fraud(
        self,
        transaction_id: str,
        order_id: str,
        user_id: str,
        amount: Decimal,
        currency: str,
        billing_country: str | None = None,
        client_ip: str | None = None,
    ) -> dict[str, Any]:
        """Call Fraud Service for risk evaluation with safe review fallback."""
        if self.fraud_client:
            try:
                res = await self.fraud_client.check(
                    transaction_id=transaction_id,
                    order_id=order_id,
                    user_id=user_id,
                    amount=amount,
                    currency=currency,
                    billing_country=billing_country,
                    client_ip=client_ip,
                )
                if isinstance(res, dict) and "decision" in res:
                    return res
            except Exception as e:
                logger.error(f"Injected fraud client error: {e}. Defaulting to REVIEW decision.")
                return {
                    "decision": FraudDecision.REVIEW.value,
                    "risk_score": 85.0,
                    "reasons": [f"Fraud client failure: {str(e)}"],
                }

        url = f"{settings.FRAUD_SERVICE_URL}/fraud/check"
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.post(
                    url,
                    json={
                        "transaction_id": transaction_id,
                        "order_id": order_id,
                        "user_id": user_id,
                        "amount": float(amount),
                        "currency": currency,
                        "billing_country": billing_country,
                        "client_ip": client_ip,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict) and "decision" in data:
                        return data
                    return {
                        "decision": FraudDecision.REVIEW.value,
                        "risk_score": 85.0,
                        "reasons": ["Malformed response payload from fraud service"],
                    }
                else:
                    logger.warning(
                        f"Fraud service returned status {resp.status_code}. Defaulting to REVIEW."
                    )
                    return {
                        "decision": FraudDecision.REVIEW.value,
                        "risk_score": 85.0,
                        "reasons": [f"Fraud service returned HTTP {resp.status_code}"],
                    }
            except Exception as e:
                logger.error(
                    f"Fraud check communication error: {e}. Defaulting to REVIEW decision for safety."
                )
                return {
                    "decision": FraudDecision.REVIEW.value,
                    "risk_score": 85.0,
                    "reasons": [f"Fraud service unreachable or timed out: {str(e)}"],
                }

    async def process_payment(
        self,
        user_id: str,
        req: PaymentCreateRequest,
    ) -> PaymentResponse:
        # 1. Idempotency Check (Pre-flight check)
        if req.idempotency_key:
            existing = await self.repository.get_by_user_idempotency(user_id, req.idempotency_key)
            if not existing:
                existing = await self.repository.get_by_idempotency_key(req.idempotency_key)
            if existing:
                logger.info(f"Returning cached payment for idempotency_key {req.idempotency_key}")
                return self._to_response(existing)

        tx_id = f"tx_{uuid.uuid4().hex[:12]}"
        payment_id = f"pay_{uuid.uuid4().hex[:16]}"
        now = datetime.now(UTC)

        # 2. Fraud Evaluation
        fraud_result = await self._check_fraud(
            transaction_id=tx_id,
            order_id=req.order_id,
            user_id=user_id,
            amount=req.amount,
            currency=req.currency or "USD",
            billing_country=req.billing_country,
            client_ip=req.client_ip,
        )

        decision = fraud_result.get("decision", FraudDecision.REVIEW.value)

        # 3. Handle Fraud REJECT
        if decision == FraudDecision.REJECT.value:
            reason = f"Payment rejected due to high fraud risk: {', '.join(fraud_result.get('reasons', []))}"
            payment = Payment(
                id=payment_id,
                order_id=req.order_id,
                user_id=user_id,
                amount=req.amount,
                currency=req.currency or "USD",
                provider="stripe" if not settings.USE_MOCK_PAYMENT_PROVIDER else "mock",
                status=PaymentStatus.FRAUD_REJECTED.value,
                idempotency_key=req.idempotency_key,
                failure_reason=reason,
                created_at=now,
                updated_at=now,
            )
            event = PaymentFailedEvent(
                payment_id=payment_id,
                order_id=req.order_id,
                user_id=user_id,
                amount=req.amount,
                currency=payment.currency,
                provider=payment.provider,
                reason=reason,
                user_email=req.user_email,
            )
            try:
                await self.repository.save_payment_with_outbox(
                    payment=payment,
                    topic="payments",
                    event_type="PaymentFailedEvent",
                    payload=event.model_dump(mode="json"),
                )
            except IntegrityError:
                await self.repository.session.rollback()
                for _ in range(5):
                    existing = await self.repository.get_by_user_idempotency(
                        user_id, req.idempotency_key
                    )
                    if not existing:
                        existing = await self.repository.get_by_idempotency_key(req.idempotency_key)
                    if existing:
                        return self._to_response(existing)
                    await asyncio.sleep(0.05)
                raise

            if self.event_bus:
                try:
                    await self.event_bus.publish("payments", event)
                except Exception as e:
                    logger.warning(f"Immediate event publish failed (outbox will deliver): {e}")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "PAYMENT_FRAUD_REJECTED", "message": reason},
            )

        # 4. Handle Fraud REVIEW / Service Failure
        if decision == FraudDecision.REVIEW.value:
            reason = f"Payment held for manual review: {', '.join(fraud_result.get('reasons', []))}"
            payment = Payment(
                id=payment_id,
                order_id=req.order_id,
                user_id=user_id,
                amount=req.amount,
                currency=req.currency or "USD",
                provider="stripe" if not settings.USE_MOCK_PAYMENT_PROVIDER else "mock",
                status=PaymentStatus.FAILED.value,
                idempotency_key=req.idempotency_key,
                failure_reason=reason,
                created_at=now,
                updated_at=now,
            )
            event = PaymentFailedEvent(
                payment_id=payment_id,
                order_id=req.order_id,
                user_id=user_id,
                amount=req.amount,
                currency=payment.currency,
                provider=payment.provider,
                reason=reason,
                user_email=req.user_email,
            )
            try:
                await self.repository.save_payment_with_outbox(
                    payment=payment,
                    topic="payments",
                    event_type="PaymentFailedEvent",
                    payload=event.model_dump(mode="json"),
                )
            except IntegrityError:
                await self.repository.session.rollback()
                for _ in range(5):
                    existing = await self.repository.get_by_user_idempotency(
                        user_id, req.idempotency_key
                    )
                    if not existing:
                        existing = await self.repository.get_by_idempotency_key(req.idempotency_key)
                    if existing:
                        return self._to_response(existing)
                    await asyncio.sleep(0.05)
                raise

            if self.event_bus:
                try:
                    await self.event_bus.publish("payments", event)
                except Exception as e:
                    logger.warning(f"Immediate event publish failed (outbox will deliver): {e}")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "PAYMENT_UNDER_REVIEW", "message": reason},
            )

        # 5. Call Payment Provider
        provider_name = "mock" if settings.USE_MOCK_PAYMENT_PROVIDER else "stripe"
        charge_res = await self.provider.create_charge(
            amount=req.amount,
            currency=req.currency or "USD",
            payment_method_id=req.payment_method_id or "pm_card_visa",
            idempotency_key=req.idempotency_key,
            metadata={"order_id": req.order_id, "user_id": user_id},
        )

        # 6. Save Payment Record & Outbox Event Atomically
        final_status = (
            PaymentStatus.SUCCEEDED.value if charge_res.success else PaymentStatus.FAILED.value
        )
        payment = Payment(
            id=payment_id,
            order_id=req.order_id,
            user_id=user_id,
            amount=req.amount,
            currency=req.currency or "USD",
            provider=provider_name,
            provider_transaction_id=charge_res.transaction_id,
            status=final_status,
            idempotency_key=req.idempotency_key,
            failure_reason=charge_res.error_message if not charge_res.success else None,
            created_at=now,
            updated_at=now,
        )

        if charge_res.success:
            event = PaymentCompletedEvent(
                payment_id=payment_id,
                order_id=payment.order_id,
                user_id=payment.user_id,
                amount=payment.amount,
                currency=payment.currency,
                provider=payment.provider,
                provider_transaction_id=charge_res.transaction_id,
                user_email=req.user_email,
            )
            event_type = "PaymentCompletedEvent"
        else:
            event = PaymentFailedEvent(
                payment_id=payment_id,
                order_id=payment.order_id,
                user_id=payment.user_id,
                amount=payment.amount,
                currency=payment.currency,
                provider=payment.provider,
                reason=charge_res.error_message or "Payment failed",
                user_email=req.user_email,
            )
            event_type = "PaymentFailedEvent"

        try:
            await self.repository.save_payment_with_outbox(
                payment=payment,
                topic="payments",
                event_type=event_type,
                payload=event.model_dump(mode="json"),
            )
        except IntegrityError:
            # Handle concurrency race on (user_id, idempotency_key)
            logger.warning(
                f"Idempotency race conflict on user_id={user_id}, idempotency_key={req.idempotency_key}. Retrieving existing record."
            )
            await self.repository.session.rollback()
            for _ in range(5):
                existing = await self.repository.get_by_user_idempotency(
                    user_id, req.idempotency_key
                )
                if not existing:
                    existing = await self.repository.get_by_idempotency_key(req.idempotency_key)
                if existing:
                    return self._to_response(existing)
                await asyncio.sleep(0.05)
            raise

        # Attempt immediate event dispatch (best effort; outbox guarantees delivery)
        if self.event_bus:
            try:
                await self.event_bus.publish("payments", event)
            except Exception as e:
                logger.warning(
                    f"Immediate event publish failed (outbox will deliver asynchronously): {e}"
                )

        if not charge_res.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "PAYMENT_FAILED",
                    "message": charge_res.error_message or "Payment failed",
                },
            )

        return PaymentResponse(
            id=payment_id,
            order_id=req.order_id,
            user_id=user_id,
            amount=req.amount,
            currency=req.currency or "USD",
            provider=provider_name,
            provider_transaction_id=charge_res.transaction_id,
            status=final_status,
            idempotency_key=req.idempotency_key,
            failure_reason=charge_res.error_message if not charge_res.success else None,
            created_at=now,
            updated_at=now,
        )

    async def get_payment(self, payment_id: str) -> PaymentResponse:
        payment = await self.repository.get_by_id(payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "PAYMENT_NOT_FOUND", "message": f"Payment {payment_id} not found"},
            )
        return self._to_response(payment)

    async def get_by_order(self, order_id: str) -> list[PaymentResponse]:
        payments = await self.repository.get_by_order_id(order_id)
        return [self._to_response(p) for p in payments]

    async def refund_payment(
        self, payment_id: str, user_id: str, is_admin: bool, req: PaymentRefundRequest
    ) -> PaymentResponse:
        payment = await self.repository.get_by_id(payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "PAYMENT_NOT_FOUND", "message": f"Payment {payment_id} not found"},
            )
        if not is_admin and payment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "FORBIDDEN", "message": "Access denied to refund this payment"},
            )
        if payment.status != PaymentStatus.SUCCEEDED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_PAYMENT_STATE",
                    "message": f"Cannot refund payment with status {payment.status}",
                },
            )

        refund_res = await self.provider.refund_charge(
            transaction_id=payment.provider_transaction_id or payment.id,
            amount=req.amount or payment.amount,
            reason=req.reason,
        )

        if not refund_res.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "REFUND_FAILED",
                    "message": refund_res.error_message or "Refund failed at provider",
                },
            )

        payment.status = PaymentStatus.REFUNDED.value

        event = PaymentRefundedEvent(
            payment_id=payment.id,
            order_id=payment.order_id,
            user_id=payment.user_id,
            amount=req.amount or payment.amount,
            currency=payment.currency,
            provider=payment.provider,
            refund_id=refund_res.refund_id,
        )

        updated = await self.repository.update_payment_with_outbox(
            payment=payment,
            topic="payments",
            event_type="PaymentRefundedEvent",
            payload=event.model_dump(mode="json"),
        )

        if self.event_bus:
            try:
                await self.event_bus.publish("payments", event)
            except Exception as e:
                logger.warning(f"Immediate refund event publish failed (outbox will deliver): {e}")

        logger.info(f"Payment {payment_id} successfully refunded")
        return self._to_response(updated)

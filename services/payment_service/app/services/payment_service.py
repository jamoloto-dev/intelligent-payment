"""Payment Service business logic layer."""

import uuid
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException, status

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
        """Call Fraud Service for risk evaluation."""
        if self.fraud_client:
            return await self.fraud_client.check(
                transaction_id=transaction_id,
                order_id=order_id,
                user_id=user_id,
                amount=amount,
                currency=currency,
                billing_country=billing_country,
                client_ip=client_ip,
            )

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
                    return resp.json()
            except Exception as e:
                logger.warning(
                    f"Fraud check communication error: {e}. Falling back to default low-risk evaluation."
                )
        return {"decision": "APPROVE", "risk_score": 0.0, "reasons": ["Default low risk profile"]}

    async def process_payment(
        self,
        user_id: str,
        req: PaymentCreateRequest,
    ) -> PaymentResponse:
        # 1. Idempotency Check
        if req.idempotency_key:
            existing = await self.repository.get_by_idempotency_key(req.idempotency_key)
            if existing:
                logger.info(f"Returning cached payment for idempotency_key {req.idempotency_key}")
                return PaymentResponse.model_validate(existing)

        tx_id = f"tx_{uuid.uuid4().hex[:12]}"

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

        decision = fraud_result.get("decision", "APPROVE")
        if decision == FraudDecision.REJECT.value:
            # Payment blocked due to fraud risk
            payment = Payment(
                order_id=req.order_id,
                user_id=user_id,
                amount=req.amount,
                currency=req.currency or "USD",
                provider="stripe" if not settings.USE_MOCK_PAYMENT_PROVIDER else "mock",
                status=PaymentStatus.FRAUD_REJECTED.value,
                idempotency_key=req.idempotency_key,
                failure_reason=f"Payment rejected due to high fraud risk: {', '.join(fraud_result.get('reasons', []))}",
            )
            created = await self.repository.create(payment)

            if self.event_bus:
                await self.event_bus.publish(
                    "payments",
                    PaymentFailedEvent(
                        payment_id=created.id,
                        order_id=req.order_id,
                        user_id=user_id,
                        amount=req.amount,
                        currency=created.currency,
                        provider=created.provider,
                        reason=created.failure_reason,
                        user_email=req.user_email,
                    ),
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "PAYMENT_FRAUD_REJECTED", "message": created.failure_reason},
            )

        # 3. Call Payment Provider
        provider_name = "mock" if settings.USE_MOCK_PAYMENT_PROVIDER else "stripe"
        charge_res = await self.provider.create_charge(
            amount=req.amount,
            currency=req.currency or "USD",
            payment_method_id=req.payment_method_id or "pm_card_visa",
            idempotency_key=req.idempotency_key,
            metadata={"order_id": req.order_id, "user_id": user_id},
        )

        # 4. Save Payment Record
        payment = Payment(
            order_id=req.order_id,
            user_id=user_id,
            amount=req.amount,
            currency=req.currency or "USD",
            provider=provider_name,
            provider_transaction_id=charge_res.transaction_id,
            status=(
                PaymentStatus.SUCCEEDED.value if charge_res.success else PaymentStatus.FAILED.value
            ),
            idempotency_key=req.idempotency_key,
            failure_reason=charge_res.error_message if not charge_res.success else None,
        )
        saved = await self.repository.create(payment)

        # 5. Publish Domain Events
        if self.event_bus:
            if charge_res.success:
                event = PaymentCompletedEvent(
                    payment_id=saved.id,
                    order_id=saved.order_id,
                    user_id=saved.user_id,
                    amount=saved.amount,
                    currency=saved.currency,
                    provider=saved.provider,
                    provider_transaction_id=charge_res.transaction_id,
                    user_email=req.user_email,
                )
                await self.event_bus.publish("payments", event)
            else:
                event = PaymentFailedEvent(
                    payment_id=saved.id,
                    order_id=saved.order_id,
                    user_id=saved.user_id,
                    amount=saved.amount,
                    currency=saved.currency,
                    provider=saved.provider,
                    reason=charge_res.error_message or "Payment failed",
                    user_email=req.user_email,
                )
                await self.event_bus.publish("payments", event)

        if not charge_res.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "PAYMENT_FAILED",
                    "message": charge_res.error_message or "Payment failed",
                },
            )

        return PaymentResponse.model_validate(saved)

    async def get_payment(self, payment_id: str) -> PaymentResponse:
        payment = await self.repository.get_by_id(payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "PAYMENT_NOT_FOUND", "message": f"Payment {payment_id} not found"},
            )
        return PaymentResponse.model_validate(payment)

    async def get_by_order(self, order_id: str) -> list[PaymentResponse]:
        payments = await self.repository.get_by_order_id(order_id)
        return [PaymentResponse.model_validate(p) for p in payments]

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
        updated = await self.repository.update(payment)

        if self.event_bus:
            event = PaymentRefundedEvent(
                payment_id=updated.id,
                order_id=updated.order_id,
                user_id=updated.user_id,
                amount=req.amount or updated.amount,
                currency=updated.currency,
                provider=updated.provider,
                refund_id=refund_res.refund_id,
            )
            await self.event_bus.publish("payments", event)

        logger.info(f"Payment {payment_id} successfully refunded")
        return PaymentResponse.model_validate(updated)

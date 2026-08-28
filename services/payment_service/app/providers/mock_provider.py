"""Mock sandbox payment provider for automated tests and offline development."""

import uuid
from decimal import Decimal
from typing import Any

from services.payment_service.app.providers.base import (
    PaymentProviderInterface,
    ProviderChargeResult,
    ProviderRefundResult,
)


class MockPaymentProvider(PaymentProviderInterface):
    """Simulates Stripe sandbox responses deterministically."""

    def __init__(self):
        self._charges: dict[str, ProviderChargeResult] = {}
        self._refunds: dict[str, ProviderRefundResult] = {}

    async def create_charge(
        self,
        amount: Decimal,
        currency: str,
        payment_method_id: str,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderChargeResult:
        # Simulate failure if payment_method_id contains 'declined' or 'fail'
        if "declined" in payment_method_id.lower() or "fail" in payment_method_id.lower():
            tx_id = f"ch_mock_failed_{uuid.uuid4().hex[:8]}"
            res = ProviderChargeResult(
                success=False,
                transaction_id=tx_id,
                amount=amount,
                currency=currency,
                status="FAILED",
                error_message="Card was declined by the issuer (simulated mock failure)",
                raw_response={"mock": True, "code": "card_declined"},
            )
            self._charges[tx_id] = res
            return res

        tx_id = f"ch_mock_succ_{uuid.uuid4().hex[:8]}"
        res = ProviderChargeResult(
            success=True,
            transaction_id=tx_id,
            amount=amount,
            currency=currency,
            status="SUCCEEDED",
            raw_response={"mock": True, "charge_id": tx_id, "idempotency_key": idempotency_key},
        )
        self._charges[tx_id] = res
        return res

    async def retrieve_charge(self, transaction_id: str) -> ProviderChargeResult:
        if transaction_id in self._charges:
            return self._charges[transaction_id]
        return ProviderChargeResult(
            success=True,
            transaction_id=transaction_id,
            amount=Decimal("100.00"),
            currency="USD",
            status="SUCCEEDED",
            raw_response={"mock": True},
        )

    async def refund_charge(
        self,
        transaction_id: str,
        amount: Decimal | None = None,
        reason: str | None = None,
    ) -> ProviderRefundResult:
        refund_id = f"re_mock_{uuid.uuid4().hex[:8]}"
        refund_amount = amount or Decimal("100.00")
        res = ProviderRefundResult(
            success=True,
            refund_id=refund_id,
            amount=refund_amount,
            status="SUCCEEDED",
        )
        self._refunds[refund_id] = res
        return res

    def verify_webhook(self, payload: bytes, signature_header: str) -> dict[str, Any]:
        return {
            "id": f"evt_mock_{uuid.uuid4().hex[:8]}",
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_mock_123", "status": "succeeded"}},
        }

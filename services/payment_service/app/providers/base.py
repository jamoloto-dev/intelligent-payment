"""Abstract base class for payment gateway providers."""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class ProviderChargeResult(BaseModel):
    success: bool
    transaction_id: str
    amount: Decimal
    currency: str
    status: str
    error_message: str | None = None
    raw_response: dict[str, Any] = {}


class ProviderRefundResult(BaseModel):
    success: bool
    refund_id: str
    amount: Decimal
    status: str
    error_message: str | None = None


class PaymentProviderInterface(ABC):
    """Clean abstraction separating payment business logic from gateway SDKs."""

    @abstractmethod
    async def create_charge(
        self,
        amount: Decimal,
        currency: str,
        payment_method_id: str,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderChargeResult:
        pass

    @abstractmethod
    async def retrieve_charge(self, transaction_id: str) -> ProviderChargeResult:
        pass

    @abstractmethod
    async def refund_charge(
        self,
        transaction_id: str,
        amount: Decimal | None = None,
        reason: str | None = None,
    ) -> ProviderRefundResult:
        pass

    @abstractmethod
    def verify_webhook(self, payload: bytes, signature_header: str) -> dict[str, Any]:
        pass

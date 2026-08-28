"""Storage abstraction for Fraud Evaluations."""

from services.fraud_service.app.schemas.fraud import FraudCheckResponse


class FraudStorage:
    """In-memory and persistent storage for fraud decisions."""

    def __init__(self):
        self._records: dict[str, FraudCheckResponse] = {}

    async def save(self, response: FraudCheckResponse) -> None:
        self._records[response.transaction_id] = response

    async def get_by_transaction_id(self, transaction_id: str) -> FraudCheckResponse | None:
        return self._records.get(transaction_id)

    async def list_evaluations(self, limit: int = 50) -> list[FraudCheckResponse]:
        return list(self._records.values())[-limit:]

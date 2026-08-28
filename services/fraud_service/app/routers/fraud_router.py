"""Fraud Service API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.fraud_service.app.schemas.fraud import FraudCheckRequest, FraudCheckResponse
from services.fraud_service.app.services.fraud_service import FraudService
from services.fraud_service.app.storage.storage import FraudStorage
from shared.authentication.dependencies import require_admin
from shared.authentication.jwt import TokenPayload

fraud_router = APIRouter(prefix="/fraud", tags=["Fraud Detection"])

_default_storage = FraudStorage()
_default_service = FraudService(storage=_default_storage)


def get_fraud_service() -> FraudService:
    return _default_service


@fraud_router.post("/check", response_model=FraudCheckResponse)
async def check_fraud(
    req: FraudCheckRequest,
    service: FraudService = Depends(get_fraud_service),
):
    """Evaluate payment transaction for potential fraud risk."""
    return await service.evaluate_transaction(req)


@fraud_router.get("/evaluations", response_model=list[FraudCheckResponse])
async def list_fraud_evaluations(
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenPayload = Depends(require_admin),
    service: FraudService = Depends(get_fraud_service),
):
    """List recent fraud evaluations (Admin only)."""
    return await service.list_evaluations(limit=limit)


@fraud_router.get("/{transaction_id}", response_model=FraudCheckResponse)
async def get_fraud_decision(
    transaction_id: str,
    service: FraudService = Depends(get_fraud_service),
):
    """Get fraud evaluation details for a transaction."""
    decision = await service.get_by_transaction_id(transaction_id)
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "FRAUD_RECORD_NOT_FOUND",
                "message": f"No fraud evaluation found for transaction {transaction_id}",
            },
        )
    return decision

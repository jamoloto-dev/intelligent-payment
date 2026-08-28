"""Payment Service API endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from services.payment_service.app.schemas.payment import (
    PaymentCreateRequest,
    PaymentRefundRequest,
    PaymentResponse,
)
from services.payment_service.app.services.payment_service import PaymentService
from shared.authentication.dependencies import (
    require_authenticated,
)
from shared.authentication.jwt import TokenPayload
from shared.schemas.common import UserRole

payment_router = APIRouter(prefix="/payments", tags=["Payments"])


def get_payment_service() -> PaymentService:
    # Overridden in main.py
    pass


@payment_router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    req: PaymentCreateRequest,
    current_user: TokenPayload = Depends(require_authenticated),
    service: PaymentService = Depends(get_payment_service),
):
    """Process a payment charge with fraud verification."""
    return await service.process_payment(user_id=current_user.sub, req=req)


@payment_router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    current_user: TokenPayload = Depends(require_authenticated),
    service: PaymentService = Depends(get_payment_service),
):
    """Retrieve payment details."""
    payment = await service.get_payment(payment_id)
    if current_user.role != UserRole.ADMIN.value and payment.user_id != current_user.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Access denied to this payment record"},
        )
    return payment


@payment_router.get("/order/{order_id}", response_model=list[PaymentResponse])
async def get_payments_for_order(
    order_id: str,
    current_user: TokenPayload = Depends(require_authenticated),
    service: PaymentService = Depends(get_payment_service),
):
    """Retrieve payment history for a specific order."""
    payments = await service.get_by_order(order_id)
    if (
        payments
        and current_user.role != UserRole.ADMIN.value
        and payments[0].user_id != current_user.sub
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Access denied to order payments"},
        )
    return payments


@payment_router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(
    payment_id: str,
    req: PaymentRefundRequest,
    current_user: TokenPayload = Depends(require_authenticated),
    service: PaymentService = Depends(get_payment_service),
):
    """Refund a previously succeeded payment."""
    is_admin = current_user.role == UserRole.ADMIN.value
    return await service.refund_payment(
        payment_id=payment_id,
        user_id=current_user.sub,
        is_admin=is_admin,
        req=req,
    )


@payment_router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="stripe-signature"),
    service: PaymentService = Depends(get_payment_service),
):
    """Handle asynchronous Stripe webhook callbacks."""
    payload_bytes = await request.body()
    try:
        event = service.provider.verify_webhook(payload_bytes, stripe_signature or "")
        event_type = event.get("type")
        return {"received": True, "event_type": event_type}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

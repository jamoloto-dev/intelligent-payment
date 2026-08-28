"""Notification Service API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from shared.authentication.dependencies import get_current_user_token, require_admin, require_authenticated
from shared.authentication.jwt import TokenPayload
from shared.schemas.common import UserRole
from services.notification_service.app.schemas.notification import (
    NotificationResponse,
    NotificationSendRequest,
)
from services.notification_service.app.services.notification_service import NotificationService
from services.notification_service.app.storage.storage import NotificationStorage

notification_router = APIRouter(prefix="/notifications", tags=["Notifications"])

_default_storage = NotificationStorage()
_default_service = NotificationService(storage=_default_storage)


def get_notification_service() -> NotificationService:
    return _default_service


@notification_router.post("/send", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def send_manual_notification(
    req: NotificationSendRequest,
    current_user: TokenPayload = Depends(require_admin),
    service: NotificationService = Depends(get_notification_service),
):
    """Manually dispatch a notification (Admin only)."""
    return await service.send_notification(req)


@notification_router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    recipient: Optional[str] = Query(None),
    current_user: TokenPayload = Depends(require_authenticated),
    service: NotificationService = Depends(get_notification_service),
):
    """Query recent notifications (Admin sees all, user sees own)."""
    if current_user.role != UserRole.ADMIN.value:
        recipient = current_user.email
    return await service.list_notifications(recipient=recipient, limit=limit)


@notification_router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    current_user: TokenPayload = Depends(require_authenticated),
    service: NotificationService = Depends(get_notification_service),
):
    """Retrieve notification details."""
    n = await service.get_by_id(notification_id)
    if not n:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOTIFICATION_NOT_FOUND", "message": f"Notification {notification_id} not found"},
        )
    if current_user.role != UserRole.ADMIN.value and n.recipient != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Access denied to notification"},
        )
    return n

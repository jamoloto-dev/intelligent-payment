"""Notification Service business logic layer."""

import uuid

from services.notification_service.app.channels.base import NotificationChannel
from services.notification_service.app.channels.email_channel import EmailNotificationChannel
from services.notification_service.app.channels.log_channel import LogNotificationChannel
from services.notification_service.app.schemas.notification import (
    NotificationResponse,
    NotificationSendRequest,
    NotificationStatus,
    NotificationType,
)
from services.notification_service.app.storage.storage import NotificationStorage
from shared.logging.logger import get_logger

logger = get_logger("notification-service")


class NotificationService:
    """Dispatches notifications across channels and stores audit records."""

    def __init__(
        self,
        channels: dict[NotificationType, NotificationChannel] | None = None,
        storage: NotificationStorage | None = None,
    ):
        self.channels = channels or {
            NotificationType.LOG: LogNotificationChannel(),
            NotificationType.EMAIL: EmailNotificationChannel(),
        }
        self.storage = storage or NotificationStorage()

    async def send_notification(self, req: NotificationSendRequest) -> NotificationResponse:
        channel = self.channels.get(req.notification_type, self.channels[NotificationType.LOG])
        success = await channel.send(
            recipient=req.recipient,
            subject=req.subject,
            body=req.body,
            metadata=req.metadata,
        )

        notification = NotificationResponse(
            id=str(uuid.uuid4()),
            recipient=req.recipient,
            subject=req.subject,
            body=req.body,
            notification_type=req.notification_type,
            status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
            event_type=req.event_type,
            metadata=req.metadata,
        )
        await self.storage.save(notification)
        return notification

    async def get_by_id(self, notification_id: str) -> NotificationResponse | None:
        return await self.storage.get_by_id(notification_id)

    async def list_notifications(
        self, recipient: str | None = None, limit: int = 50
    ) -> list[NotificationResponse]:
        return await self.storage.list_notifications(recipient=recipient, limit=limit)

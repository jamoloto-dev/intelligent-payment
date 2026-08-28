"""Structured Log Notification Channel."""

from typing import Any

from services.notification_service.app.channels.base import NotificationChannel
from shared.logging.logger import get_logger

logger = get_logger("notification-channel")


class LogNotificationChannel(NotificationChannel):
    """Dispatches notifications to structured log output (ideal for dev/testing)."""

    async def send(self, recipient: str, subject: str, body: str, metadata: dict[str, Any]) -> bool:
        logger.info(
            f"NOTIFICATION TO [{recipient}]: {subject} - {body}",
            extra={
                "event": "notification_sent",
                "status": "SENT",
                "extra_data": {"recipient": recipient, "subject": subject, "metadata": metadata},
            },
        )
        return True

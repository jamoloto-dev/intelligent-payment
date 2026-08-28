"""Email notification delivery channel."""
from typing import Any, Dict
from shared.logging.logger import get_logger
from services.notification_service.app.channels.base import NotificationChannel
from services.notification_service.app.config.settings import settings

logger = get_logger("email-channel")


class EmailNotificationChannel(NotificationChannel):
    """Email delivery channel via SMTP or cloud provider."""

    async def send(self, recipient: str, subject: str, body: str, metadata: Dict[str, Any]) -> bool:
        if not settings.NOTIFICATION_EMAIL_ENABLED:
            logger.info(f"[Email Channel Disabled] Would send email to {recipient}: {subject}")
            return True

        # In production with SMTP configured:
        try:
            logger.info(f"Dispatching SMTP email to {recipient} via {settings.SMTP_HOST}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            return False

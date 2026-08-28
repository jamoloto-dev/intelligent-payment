"""Storage for dispatched notifications."""
from typing import Dict, List, Optional
from services.notification_service.app.schemas.notification import NotificationResponse


class NotificationStorage:
    """In-memory and persistent notification history."""

    def __init__(self):
        self._notifications: Dict[str, NotificationResponse] = {}

    async def save(self, notification: NotificationResponse) -> None:
        self._notifications[notification.id] = notification

    async def get_by_id(self, notification_id: str) -> Optional[NotificationResponse]:
        return self._notifications.get(notification_id)

    async def list_notifications(
        self,
        recipient: Optional[str] = None,
        limit: int = 50,
    ) -> List[NotificationResponse]:
        items = list(self._notifications.values())
        if recipient:
            items = [n for n in items if n.recipient == recipient]
        return items[-limit:]

"""Storage for dispatched notifications."""

from services.notification_service.app.schemas.notification import NotificationResponse


class NotificationStorage:
    """In-memory and persistent notification history."""

    def __init__(self):
        self._notifications: dict[str, NotificationResponse] = {}

    async def save(self, notification: NotificationResponse) -> None:
        self._notifications[notification.id] = notification

    async def get_by_id(self, notification_id: str) -> NotificationResponse | None:
        return self._notifications.get(notification_id)

    async def list_notifications(
        self,
        recipient: str | None = None,
        limit: int = 50,
    ) -> list[NotificationResponse]:
        items = list(self._notifications.values())
        if recipient:
            items = [n for n in items if n.recipient == recipient]
        return items[-limit:]

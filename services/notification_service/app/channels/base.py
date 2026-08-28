"""Abstract base class for notification delivery channels."""

from abc import ABC, abstractmethod
from typing import Any


class NotificationChannel(ABC):
    """Channel interface for dispatching notifications."""

    @abstractmethod
    async def send(self, recipient: str, subject: str, body: str, metadata: dict[str, Any]) -> bool:
        pass

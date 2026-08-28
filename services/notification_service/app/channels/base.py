"""Abstract base class for notification delivery channels."""
from abc import ABC, abstractmethod
from typing import Any, Dict


class NotificationChannel(ABC):
    """Channel interface for dispatching notifications."""

    @abstractmethod
    async def send(self, recipient: str, subject: str, body: str, metadata: Dict[str, Any]) -> bool:
        pass

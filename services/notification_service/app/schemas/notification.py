"""Notification schemas."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from shared.schemas.common import BaseResponse


class NotificationType(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    LOG = "LOG"
    WEBHOOK = "WEBHOOK"


class NotificationStatus(str, Enum):
    SENT = "SENT"
    FAILED = "FAILED"
    QUEUED = "QUEUED"


class NotificationSendRequest(BaseModel):
    recipient: str = Field(..., description="Email address or user identifier")
    subject: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    notification_type: NotificationType = Field(default=NotificationType.LOG)
    event_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationResponse(BaseResponse):
    id: str
    recipient: str
    subject: str
    body: str
    notification_type: NotificationType
    status: NotificationStatus
    event_type: Optional[str] = None
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = {}

"""Structured JSON logging with security sanitization."""

import contextvars
import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# Context variables for tracing across async execution
request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
user_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)

# Patterns for sensitive keys that must be redacted
SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "jwt_secret",
    "secret",
    "api_key",
    "stripe_secret_key",
    "webhook_secret",
    "credit_card",
    "card_number",
    "cvv",
    "authorization",
}

REDACTED = "[REDACTED]"


def sanitize_data(data: Any) -> Any:
    """Recursively redact sensitive key values and secrets."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if any(sensitive in k.lower() for sensitive in SENSITIVE_KEYS):
                sanitized[k] = REDACTED
            elif isinstance(v, (dict, list)):
                sanitized[k] = sanitize_data(v)
            elif isinstance(v, str) and ("Bearer " in v or "sk_test_" in v or "whsec_" in v):
                sanitized[k] = REDACTED
            else:
                sanitized[k] = v
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    return data


class JSONFormatter(logging.Formatter):
    """Custom Formatter outputting structured JSON logs."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "service": self.service_name,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
            "user_id": user_id_ctx.get(),
        }

        # Include custom extra fields attached to the log record
        if hasattr(record, "event"):
            log_data["event"] = record.event
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
        if hasattr(record, "extra_data"):
            log_data["extra_data"] = sanitize_data(record.extra_data)

        if record.exc_info:
            log_data["error"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def get_logger(service_name: str, level: str = "INFO") -> logging.Logger:
    """Configures and returns a structured logger for a service."""
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter(service_name))
        logger.addHandler(handler)
        logger.propagate = False

    return logger

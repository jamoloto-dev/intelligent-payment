"""Notification Service main FastAPI application entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from services.notification_service.app.config.settings import settings
from services.notification_service.app.consumers.event_consumer import NotificationEventConsumer
from services.notification_service.app.routers.notification_router import (
    get_notification_service,
    notification_router,
)
from services.notification_service.app.services.notification_service import NotificationService
from services.notification_service.app.storage.storage import NotificationStorage
from shared.events.redis_client import EventBus
from shared.logging.logger import get_logger
from shared.logging.middleware import RequestLoggingMiddleware
from shared.schemas.common import HealthCheckResponse, HealthStatus
from shared.schemas.errors import HTTPErrorResponse

logger = get_logger("notification-service")

event_bus = EventBus(redis_url=settings.REDIS_URL)
notification_storage = NotificationStorage()
notification_service_instance = NotificationService(storage=notification_storage)
consumer = NotificationEventConsumer(event_bus, notification_service_instance)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Notification Service...")
    await event_bus.connect()
    consumer.register_handlers()
    await event_bus.start_listening(channels=["orders", "payments", "fraud_events"])
    yield
    logger.info("Shutting down Notification Service...")
    await event_bus.disconnect()


app = FastAPI(
    title="Notification Service",
    description="Microservice for Asynchronous Multi-Channel Event Notifications and Logs",
    version="1.0.0",
    lifespan=lifespan,
    responses={
        400: {"model": HTTPErrorResponse},
        401: {"model": HTTPErrorResponse},
        403: {"model": HTTPErrorResponse},
        404: {"model": HTTPErrorResponse},
        422: {"model": HTTPErrorResponse},
        500: {"model": HTTPErrorResponse},
    },
)

app.add_middleware(RequestLoggingMiddleware, service_name=settings.SERVICE_NAME)


# Dependency injection
async def get_notification_service_dependency() -> AsyncGenerator[NotificationService, None]:
    yield notification_service_instance


app.dependency_overrides[get_notification_service] = get_notification_service_dependency


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = request.headers.get("X-Request-ID")
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail.get("error", "HTTP_ERROR"),
                "message": exc.detail.get("message", str(exc.detail)),
                "request_id": request_id,
                "details": exc.detail.get("details"),
            },
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": str(exc.detail),
            "request_id": request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("X-Request-ID")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid request payload",
            "request_id": request_id,
            "details": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID")
    logger.exception("Unhandled server error", extra={"event": "unhandled_exception"})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "request_id": request_id,
        },
    )


app.include_router(notification_router)


# Health and Readiness Probes
@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health():
    return HealthCheckResponse(service="notification-service", status=HealthStatus.HEALTHY)


@app.get("/ready", response_model=HealthCheckResponse, tags=["Health"])
async def ready():
    redis_ok = event_bus._running
    return HealthCheckResponse(
        service="notification-service",
        status=HealthStatus.HEALTHY if redis_ok else HealthStatus.DEGRADED,
        dependencies={"redis": "connected" if redis_ok else "disconnected"},
    )

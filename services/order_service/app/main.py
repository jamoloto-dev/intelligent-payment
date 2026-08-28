"""Order Service main FastAPI application entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from services.order_service.app.config.settings import settings
from services.order_service.app.repositories.order_repository import OrderRepository
from services.order_service.app.routers.order_router import get_order_service, order_router
from services.order_service.app.services.order_service import OrderService
from shared.database.base import Base
from shared.database.session import check_db_health, create_db_engine, create_session_factory
from shared.events.redis_client import EventBus
from shared.logging.logger import get_logger
from shared.logging.middleware import RequestLoggingMiddleware
from shared.schemas.common import HealthCheckResponse, HealthStatus, OrderStatus
from shared.schemas.errors import HTTPErrorResponse

logger = get_logger("order-service")

# Database & Event Bus
engine = create_db_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = create_session_factory(engine)
event_bus = EventBus(redis_url=settings.REDIS_URL)


async def handle_payment_completed(event_data: dict):
    """Event handler updating order status when payment succeeds."""
    order_id = event_data.get("order_id")
    if not order_id:
        return
    logger.info(f"Received PaymentCompleted for order {order_id}")
    async with SessionLocal() as session:
        service = OrderService(OrderRepository(session), event_bus=event_bus)
        try:
            await service.update_status(order_id, OrderStatus.PAID)
        except Exception as e:
            logger.error(f"Failed to update order {order_id} on PaymentCompleted: {e}")


async def handle_payment_failed(event_data: dict):
    """Event handler updating order status when payment fails."""
    order_id = event_data.get("order_id")
    if not order_id:
        return
    logger.info(f"Received PaymentFailed for order {order_id}")
    async with SessionLocal() as session:
        service = OrderService(OrderRepository(session), event_bus=event_bus)
        try:
            await service.update_status(
                order_id, OrderStatus.FAILED, reason=event_data.get("reason")
            )
        except Exception as e:
            logger.error(f"Failed to update order {order_id} on PaymentFailed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Order Service...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Order Service database tables initialized")

    # Connect to Event Bus and register subscribers
    await event_bus.connect()
    event_bus.subscribe("PaymentCompleted", handle_payment_completed)
    event_bus.subscribe("PaymentFailed", handle_payment_failed)
    await event_bus.start_listening(channels=["payments", "PaymentCompleted", "PaymentFailed"])

    yield

    logger.info("Shutting down Order Service...")
    await event_bus.disconnect()
    await engine.dispose()


app = FastAPI(
    title="Order Service",
    description="Microservice for Order Management, Inventory Coordination, and Order Lifecycle",
    version="1.0.0",
    lifespan=lifespan,
    responses={
        400: {"model": HTTPErrorResponse},
        401: {"model": HTTPErrorResponse},
        403: {"model": HTTPErrorResponse},
        404: {"model": HTTPErrorResponse},
        409: {"model": HTTPErrorResponse},
        422: {"model": HTTPErrorResponse},
        500: {"model": HTTPErrorResponse},
    },
)

app.add_middleware(RequestLoggingMiddleware, service_name=settings.SERVICE_NAME)


# Dependency injection for OrderService
async def get_order_service_dependency() -> AsyncGenerator[OrderService, None]:
    async with SessionLocal() as session:
        repo = OrderRepository(session)
        yield OrderService(repo, event_bus=event_bus)


app.dependency_overrides[get_order_service] = get_order_service_dependency


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


app.include_router(order_router)


# Health and Readiness Probes
@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health():
    return HealthCheckResponse(service="order-service", status=HealthStatus.HEALTHY)


@app.get("/ready", response_model=HealthCheckResponse, tags=["Health"])
async def ready():
    db_ok = await check_db_health(engine)
    redis_ok = event_bus._running
    status_val = HealthStatus.HEALTHY if (db_ok and redis_ok) else HealthStatus.DEGRADED
    return HealthCheckResponse(
        service="order-service",
        status=status_val,
        dependencies={
            "database": "connected" if db_ok else "disconnected",
            "redis": "connected" if redis_ok else "disconnected",
        },
    )

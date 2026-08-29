"""Payment Service main FastAPI application entrypoint."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from services.payment_service.app.config.settings import settings
from services.payment_service.app.events.outbox_processor import OutboxProcessor
from services.payment_service.app.providers.mock_provider import MockPaymentProvider
from services.payment_service.app.providers.stripe_provider import StripePaymentProvider
from services.payment_service.app.repositories.payment_repository import PaymentRepository
from services.payment_service.app.routers.payment_router import get_payment_service, payment_router
from services.payment_service.app.services.payment_service import PaymentService
from shared.database.base import Base
from shared.database.session import check_db_health, create_db_engine, create_session_factory
from shared.events.redis_client import EventBus
from shared.logging.logger import get_logger
from shared.logging.middleware import RequestLoggingMiddleware
from shared.schemas.common import HealthCheckResponse, HealthStatus
from shared.schemas.errors import HTTPErrorResponse

logger = get_logger("payment-service")

# Database & Event Bus
engine = create_db_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = create_session_factory(engine)
event_bus = EventBus(redis_url=settings.REDIS_URL)
outbox_processor = OutboxProcessor(session_factory=SessionLocal, event_bus=event_bus)

# Provider initialization
if settings.USE_MOCK_PAYMENT_PROVIDER or not settings.STRIPE_SECRET_KEY.startswith("sk_"):
    payment_provider = MockPaymentProvider()
else:
    payment_provider = StripePaymentProvider(
        api_key=settings.STRIPE_SECRET_KEY,
        webhook_secret=settings.STRIPE_WEBHOOK_SECRET,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Payment Service...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Payment Service database tables initialized")

    await event_bus.connect()
    outbox_task = asyncio.create_task(outbox_processor.start(poll_interval_seconds=2.0))

    yield

    logger.info("Shutting down Payment Service...")
    outbox_processor.stop()
    outbox_task.cancel()
    try:
        await outbox_task
    except asyncio.CancelledError:
        pass

    await event_bus.disconnect()
    await engine.dispose()


app = FastAPI(
    title="Payment Service",
    description="Microservice for Payment Processing, Stripe Integration, Idempotency, and Refunds",
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


# Dependency injection
async def get_payment_service_dependency() -> AsyncGenerator[PaymentService, None]:
    async with SessionLocal() as session:
        repo = PaymentRepository(session)
        yield PaymentService(repository=repo, provider=payment_provider, event_bus=event_bus)


app.dependency_overrides[get_payment_service] = get_payment_service_dependency


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


app.include_router(payment_router)


# Health and Readiness Probes
@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health():
    return HealthCheckResponse(service="payment-service", status=HealthStatus.HEALTHY)


@app.get("/ready", response_model=HealthCheckResponse, tags=["Health"])
async def ready(response: Response):
    db_ok = await check_db_health(engine)
    redis_ok = event_bus._running
    status_val = HealthStatus.HEALTHY if (db_ok and redis_ok) else HealthStatus.DEGRADED
    if status_val != HealthStatus.HEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthCheckResponse(
        service="payment-service",
        status=status_val,
        dependencies={
            "database": "connected" if db_ok else "disconnected",
            "redis": "connected" if redis_ok else "disconnected",
        },
    )

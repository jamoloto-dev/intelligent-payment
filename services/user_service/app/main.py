"""User Service main FastAPI application entrypoint."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from shared.database.base import Base
from shared.database.session import check_db_health, create_db_engine, create_session_factory
from shared.logging.logger import get_logger
from shared.logging.middleware import RequestLoggingMiddleware
from shared.schemas.common import HealthCheckResponse, HealthStatus
from shared.schemas.errors import HTTPErrorResponse
from services.user_service.app.config.settings import settings
from services.user_service.app.repositories.user_repository import UserRepository
from services.user_service.app.routers.user_router import auth_router, get_user_service, users_router
from services.user_service.app.services.user_service import UserService

logger = get_logger("user-service")

# Database setup
engine = create_db_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = create_session_factory(engine)


async def get_db() -> AsyncGenerator:
    async with SessionLocal() as session:
        yield session


def get_service_override(session=None) -> UserService:
    # Dependency override helper
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up User Service...")
    # Initialize tables if needed
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("User Service database tables initialized")
    yield
    logger.info("Shutting down User Service...")
    await engine.dispose()


app = FastAPI(
    title="User Service",
    description="Microservice for User Registration, Authentication, and Profile Management",
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

# Attach Logging Middleware
app.add_middleware(RequestLoggingMiddleware, service_name=settings.SERVICE_NAME)

# Dependency overrides for database session
async def get_user_service_dependency() -> AsyncGenerator[UserService, None]:
    async with SessionLocal() as session:
        repo = UserRepository(session)
        yield UserService(repo)

app.dependency_overrides[get_user_service] = get_user_service_dependency


# Standard Error Handlers
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
            "message": "Invalid request parameters or payload",
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
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": request_id,
        },
    )


# Routers
app.include_router(auth_router)
app.include_router(users_router)


# Health and Readiness Probes
@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health():
    return HealthCheckResponse(service="user-service", status=HealthStatus.HEALTHY)


@app.get("/ready", response_model=HealthCheckResponse, tags=["Health"])
async def ready():
    db_ok = await check_db_health(engine)
    status_val = HealthStatus.HEALTHY if db_ok else HealthStatus.UNHEALTHY
    return HealthCheckResponse(
        service="user-service",
        status=status_val,
        dependencies={"database": "connected" if db_ok else "disconnected"},
    )

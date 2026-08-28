"""Product Service main FastAPI application entrypoint."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
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
from services.product_service.app.config.settings import settings
from services.product_service.app.repositories.product_repository import ProductRepository
from services.product_service.app.routers.product_router import get_product_service, product_router
from services.product_service.app.services.product_service import ProductService

logger = get_logger("product-service")

engine = create_db_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = create_session_factory(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Product Service...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Product Service database tables initialized")
    yield
    logger.info("Shutting down Product Service...")
    await engine.dispose()


app = FastAPI(
    title="Product Service",
    description="Microservice for Product Catalog and Atomic Inventory Management",
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


async def get_product_service_dependency() -> AsyncGenerator[ProductService, None]:
    async with SessionLocal() as session:
        repo = ProductRepository(session)
        yield ProductService(repo)

app.dependency_overrides[get_product_service] = get_product_service_dependency


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


app.include_router(product_router)


@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health():
    return HealthCheckResponse(service="product-service", status=HealthStatus.HEALTHY)


@app.get("/ready", response_model=HealthCheckResponse, tags=["Health"])
async def ready():
    db_ok = await check_db_health(engine)
    status_val = HealthStatus.HEALTHY if db_ok else HealthStatus.UNHEALTHY
    return HealthCheckResponse(
        service="product-service",
        status=status_val,
        dependencies={"database": "connected" if db_ok else "disconnected"},
    )

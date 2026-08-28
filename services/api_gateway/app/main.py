"""API Gateway Main Entrypoint."""
import asyncio
from contextlib import asynccontextmanager
from typing import Dict
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from shared.logging.logger import get_logger
from shared.logging.middleware import RequestLoggingMiddleware
from shared.schemas.common import HealthCheckResponse, HealthStatus
from shared.schemas.errors import HTTPErrorResponse
from services.api_gateway.app.config.settings import settings
from services.api_gateway.app.middleware.rate_limit import RateLimitMiddleware
from services.api_gateway.app.routers.proxy_router import http_client, proxy_router

logger = get_logger("api-gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"API Gateway starting on port {settings.PORT}...")
    yield
    logger.info("API Gateway shutting down...")
    await http_client.aclose()


app = FastAPI(
    title="Intelligent Payment & Order Platform - API Gateway",
    description="Unified API Gateway exposing microservices for Authentication, Products, Orders, Payments, Fraud Prevention, and Notifications.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    responses={
        400: {"model": HTTPErrorResponse},
        401: {"model": HTTPErrorResponse},
        403: {"model": HTTPErrorResponse},
        404: {"model": HTTPErrorResponse},
        429: {"model": HTTPErrorResponse},
        500: {"model": HTTPErrorResponse},
        503: {"model": HTTPErrorResponse},
    },
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Logging & Rate Limiting
app.add_middleware(RateLimitMiddleware, max_requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE)
app.add_middleware(RequestLoggingMiddleware, service_name=settings.SERVICE_NAME)


# Health & Readiness Probes
@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health():
    return HealthCheckResponse(service="api-gateway", status=HealthStatus.HEALTHY)


@app.get("/ready", response_model=HealthCheckResponse, tags=["Health"])
async def ready():
    services_to_check = {
        "user-service": f"{settings.USER_SERVICE_URL}/health",
        "product-service": f"{settings.PRODUCT_SERVICE_URL}/health",
        "order-service": f"{settings.ORDER_SERVICE_URL}/health",
        "fraud-service": f"{settings.FRAUD_SERVICE_URL}/health",
        "payment-service": f"{settings.PAYMENT_SERVICE_URL}/health",
        "notification-service": f"{settings.NOTIFICATION_SERVICE_URL}/health",
    }

    results: Dict[str, str] = {}
    async def check_svc(name: str, url: str):
        try:
            resp = await http_client.get(url, timeout=1.5)
            results[name] = "reachable" if resp.status_code == 200 else f"status_{resp.status_code}"
        except Exception:
            results[name] = "unreachable"

    await asyncio.gather(*(check_svc(n, u) for n, u in services_to_check.items()))

    all_reachable = all(v == "reachable" for v in results.values())
    status_val = HealthStatus.HEALTHY if all_reachable else HealthStatus.DEGRADED

    return HealthCheckResponse(
        service="api-gateway",
        status=status_val,
        dependencies=results,
    )


# Attach Reverse Proxy Router
app.include_router(proxy_router)

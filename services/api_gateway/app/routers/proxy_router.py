"""Reverse Proxy forwarding routes to downstream microservices."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
from shared.logging.logger import get_logger
from services.api_gateway.app.config.settings import settings

logger = get_logger("api-gateway")
proxy_router = APIRouter()

# HTTP Client for proxying
http_client = httpx.AsyncClient(timeout=15.0)

# Path prefixes mapped to target service URLs
SERVICE_MAP = {
    "/auth": settings.USER_SERVICE_URL,
    "/users": settings.USER_SERVICE_URL,
    "/products": settings.PRODUCT_SERVICE_URL,
    "/orders": settings.ORDER_SERVICE_URL,
    "/fraud": settings.FRAUD_SERVICE_URL,
    "/payments": settings.PAYMENT_SERVICE_URL,
    "/notifications": settings.NOTIFICATION_SERVICE_URL,
}


def get_target_url(path: str) -> Optional[str]:
    for prefix, base_url in SERVICE_MAP.items():
        if path == prefix or path.startswith(prefix + "/") or path.startswith(prefix + "?"):
            return base_url + path
    return None


@proxy_router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def forward_request(request: Request, path: str):
    full_path = f"/{path}"
    target_url = get_target_url(full_path)

    if not target_url:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "ROUTE_NOT_FOUND",
                "message": f"Path '{full_path}' does not match any registered microservice route.",
                "request_id": request.headers.get("X-Request-ID"),
            },
        )

    # Forward headers while preserving correlation IDs
    forward_headers = dict(request.headers)
    forward_headers.pop("host", None)
    forward_headers.pop("content-length", None)

    try:
        body = await request.body()
        req_params = dict(request.query_params)

        downstream_resp = await http_client.request(
            method=request.method,
            url=target_url,
            headers=forward_headers,
            params=req_params,
            content=body,
        )

        response_headers = dict(downstream_resp.headers)
        response_headers.pop("content-encoding", None)
        response_headers.pop("content-length", None)
        response_headers.pop("transfer-encoding", None)

        return Response(
            content=downstream_resp.content,
            status_code=downstream_resp.status_code,
            headers=response_headers,
            media_type=downstream_resp.headers.get("content-type"),
        )
    except httpx.ConnectError:
        logger.error(f"Downstream service unavailable at {target_url}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "SERVICE_UNAVAILABLE",
                "message": "The requested downstream microservice is temporarily unreachable.",
                "request_id": request.headers.get("X-Request-ID"),
            },
        )
    except httpx.TimeoutException:
        logger.error(f"Downstream timeout connecting to {target_url}")
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={
                "error": "GATEWAY_TIMEOUT",
                "message": "Downstream service request timed out.",
                "request_id": request.headers.get("X-Request-ID"),
            },
        )
    except Exception as e:
        logger.exception(f"Proxy forwarding exception: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "GATEWAY_INTERNAL_ERROR",
                "message": "Gateway encountered an error processing the request.",
                "request_id": request.headers.get("X-Request-ID"),
            },
        )

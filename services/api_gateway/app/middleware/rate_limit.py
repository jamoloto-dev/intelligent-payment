"""In-memory sliding window rate limiting middleware."""
import time
from collections import defaultdict
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Protects services against volumetric bursts and abuse."""

    def __init__(self, app, max_requests_per_minute: int = 120):
        super().__init__(app)
        self.max_requests = max_requests_per_minute
        self.window_seconds = 60
        self._history: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # Exclude health endpoints from rate limiting
        if request.url.path in ["/health", "/ready", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old timestamps
        timestamps = [ts for ts in self._history[client_ip] if ts > window_start]
        self._history[client_ip] = timestamps

        if len(timestamps) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down and try again later.",
                    "request_id": request.headers.get("X-Request-ID"),
                },
                headers={"Retry-After": "60"},
            )

        self._history[client_ip].append(now)
        return await call_next(request)

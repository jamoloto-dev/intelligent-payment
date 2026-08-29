"""Distributed Redis-backed sliding window rate limiting middleware."""

import time
import uuid
from collections import defaultdict

import redis.asyncio as aioredis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse

from shared.logging.logger import get_logger

logger = get_logger("gateway-rate-limiter")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Protects services against volumetric bursts using distributed Redis sliding window with in-memory fallback."""

    def __init__(
        self,
        app,
        max_requests_per_minute: int = 120,
        redis_url: str | None = None,
        redis_client: aioredis.Redis | None = None,
    ):
        super().__init__(app)
        self.max_requests = max_requests_per_minute
        self.window_seconds = 60
        self.redis_url = redis_url
        self.redis = redis_client
        self._redis_connected = False
        self._history: dict[str, list[float]] = defaultdict(list)

    async def _get_redis(self) -> aioredis.Redis | None:
        if self.redis is not None:
            return self.redis
        if self.redis_url:
            try:
                self.redis = aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=1.0,
                    socket_connect_timeout=1.0,
                )
                self._redis_connected = True
                return self.redis
            except Exception as e:
                logger.warning(
                    f"Could not connect to Redis for rate limiting: {e}. Using in-memory fallback."
                )
        return None

    async def _check_rate_limit_redis(self, client_ip: str, now: float) -> tuple[bool, int, int]:
        """Check rate limit via Redis sorted set sliding window."""
        r = await self._get_redis()
        if not r:
            return self._check_rate_limit_memory(client_ip, now)

        key = f"ratelimit:{client_ip}"
        window_start = now - self.window_seconds
        member_id = f"{now}:{uuid.uuid4().hex[:6]}"

        try:
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.expire(key, self.window_seconds + 5)
            results = await pipe.execute()

            current_count = results[1]
            if current_count >= self.max_requests:
                remaining = 0
                return True, remaining, int(self.window_seconds)

            # Record this request
            pipe = r.pipeline()
            pipe.zadd(key, {member_id: now})
            pipe.expire(key, self.window_seconds + 5)
            await pipe.execute()

            remaining = max(0, self.max_requests - current_count - 1)
            return False, remaining, int(self.window_seconds)
        except Exception as e:
            logger.debug(f"Redis rate limiter exception ({e}), falling back to memory.")
            return self._check_rate_limit_memory(client_ip, now)

    def _check_rate_limit_memory(self, client_ip: str, now: float) -> tuple[bool, int, int]:
        """Fallback in-memory sliding window."""
        window_start = now - self.window_seconds
        timestamps = [ts for ts in self._history[client_ip] if ts > window_start]
        self._history[client_ip] = timestamps

        if len(timestamps) >= self.max_requests:
            remaining = 0
            return True, remaining, int(self.window_seconds)

        self._history[client_ip].append(now)
        remaining = max(0, self.max_requests - len(self._history[client_ip]))
        return False, remaining, int(self.window_seconds)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # Exclude health endpoints, docs, and schema definitions from rate limiting
        if request.url.path in [
            "/health",
            "/ready",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
        ]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        now = time.time()
        exceeded, remaining, reset_time = await self._check_rate_limit_redis(client_ip, now)

        if exceeded:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down and try again later.",
                    "request_id": request.headers.get("X-Request-ID"),
                },
                headers={
                    "Retry-After": str(reset_time),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

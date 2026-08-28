"""FastAPI middleware for Request Tracing and Structured HTTP Logging."""
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from shared.logging.logger import get_logger, request_id_ctx, user_id_ctx


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware attaching request_id, tracking duration, and logging HTTP calls."""
    
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name
        self.logger = get_logger(service_name)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract or generate Request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token_req = request_id_ctx.set(request_id)
        
        # Start timing
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            # Attach X-Request-ID header to response
            response.headers["X-Request-ID"] = request_id
            
            # Log successful / standard request
            extra = {
                "event": "http_request",
                "status": response.status_code,
                "duration": f"{duration_ms}ms",
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else "unknown",
                }
            }
            if response.status_code >= 500:
                self.logger.error(f"{request.method} {request.url.path} -> {response.status_code}", extra=extra)
            elif response.status_code >= 400:
                self.logger.warning(f"{request.method} {request.url.path} -> {response.status_code}", extra=extra)
            else:
                self.logger.info(f"{request.method} {request.url.path} -> {response.status_code}", extra=extra)
                
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self.logger.exception(
                f"Unhandled Exception: {request.method} {request.url.path}",
                extra={
                    "event": "http_request_exception",
                    "status": 500,
                    "duration": f"{duration_ms}ms",
                    "extra_data": {"method": request.method, "path": request.url.path}
                }
            )
            raise exc
        finally:
            request_id_ctx.reset(token_req)

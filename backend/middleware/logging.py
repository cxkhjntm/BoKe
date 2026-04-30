"""Request logging middleware.

Logs every API request: method, path, status_code, latency_ms.
Generates/propagates X-Request-ID for correlation.
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.utils.logger import get_logger

logger = get_logger("middleware.logging")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip static assets
        if request.url.path.startswith("/assets/"):
            return await call_next(request)

        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        start = time.perf_counter()

        response = await call_next(request)

        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "%s %s %d %.1fms rid=%s",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
            request_id,
        )

        response.headers["X-Request-ID"] = request_id
        return response

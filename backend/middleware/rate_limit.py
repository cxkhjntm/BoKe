import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.utils.logger import get_logger

logger = get_logger("middleware.rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding window rate limiter.

    NOTE: Single-instance only. State is lost on process restart.
    For multi-instance deployments, replace with Redis-backed implementation.
    """

    def __init__(self, app, rules: dict[str, tuple[int, int]] | None = None):
        super().__init__(app)
        # rules: { "path_pattern": (max_requests, window_seconds) }
        self.rules = rules or {}
        self._windows: dict[str, deque] = defaultdict(deque)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup(self, key: str, window_seconds: int) -> None:
        """Lazy cleanup of expired timestamps."""
        now = time.time()
        dq = self._windows[key]
        while dq and dq[0] <= now - window_seconds:
            dq.popleft()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        for pattern, (max_req, window_sec) in self.rules.items():
            if path == pattern and method == "POST":
                client_ip = self._get_client_ip(request)
                key = f"{client_ip}:{pattern}"
                self._cleanup(key, window_sec)

                if len(self._windows[key]) >= max_req:
                    logger.warning("Rate limit exceeded for %s on %s", client_ip, pattern)
                    return JSONResponse(
                        status_code=429,
                        content={
                            "code": 4029,
                            "message": "Too many requests",
                            "data": None,
                        },
                    )

                self._windows[key].append(time.time())
                break

        return await call_next(request)

import logging
import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/v1/proceso": (10, 60),
    "/api/v1/proceso/status": (60, 60),
    "/api/v1/proceso/results": (30, 60),
    "/api/v1/proceso/errors": (30, 60),
    "/api/v1/analizar": (5, 60),
    "/api/v1/health": (0, 0),
}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        limit_config = None
        for prefix, config in RATE_LIMITS.items():
            if path.startswith(prefix):
                limit_config = config
                break

        if limit_config:
            max_req, window = limit_config
            if max_req > 0:
                client_key = f"{request.client.host}:{path}" if request.client else path
                now = time.time()
                window_start = now - window

                self._requests[client_key] = [t for t in self._requests[client_key] if t > window_start]

                if len(self._requests[client_key]) >= max_req:
                    logger.warning("Rate limit excedido para %s", client_key)
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "RATE_LIMIT_EXCEEDED",
                            "mensaje": f"Límite de requests excedido. Intente en {window} segundos.",
                        },
                    )

                self._requests[client_key].append(now)

        return await call_next(request)

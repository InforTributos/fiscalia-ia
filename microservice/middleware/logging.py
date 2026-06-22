import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("fiscalia")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""

        logger.info({
            "event": "request_start",
            "request_id": request_id,
            "method": method,
            "path": path,
            "query": query,
        })

        start = time.time()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            elapsed_ms = int((time.time() - start) * 1000)
            logger.error({
                "event": "request_error",
                "request_id": request_id,
                "method": method,
                "path": path,
                "status": 500,
                "tiempo_ms": elapsed_ms,
                "error": str(exc),
            })
            raise

        elapsed_ms = int((time.time() - start) * 1000)
        logger.info({
            "event": "request_end",
            "request_id": request_id,
            "method": method,
            "path": path,
            "status": response.status_code,
            "tiempo_ms": elapsed_ms,
        })

        return response

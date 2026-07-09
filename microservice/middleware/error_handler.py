import logging

from domain.errors import FiscalIAError
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("fiscalia")


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_error_handlers(app: FastAPI):
    @app.exception_handler(FiscalIAError)
    async def fiscalia_error_handler(request: Request, exc: FiscalIAError):
        logger.warning({
            "event": "fiscalia_error",
            "request_id": _request_id(request),
            "codigo": exc.codigo,
            "mensaje": exc.mensaje,
            "status": exc.status_code,
        })
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.codigo,
                "mensaje": exc.mensaje,
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning({
            "event": "http_error",
            "request_id": _request_id(request),
            "status_code": exc.status_code,
            "mensaje": str(exc.detail),
        })
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail if isinstance(exc.detail, dict) else {"error": "HTTP_ERROR", "mensaje": str(exc.detail)},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning({
            "event": "validation_error",
            "request_id": _request_id(request),
            "errors": exc.errors(),
        })
        return JSONResponse(
            status_code=422,
            content={
                "error": "VALIDATION_ERROR",
                "mensaje": "Error de validación en la solicitud",
                "detalle": exc.errors(),
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error({
            "event": "unhandled_error",
            "request_id": _request_id(request),
            "error": str(exc),
            "type": exc.__class__.__name__,
        })
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "mensaje": "Error interno del servidor",
                "request_id": _request_id(request),
            },
        )

from contextlib import asynccontextmanager

from config import setup_logging
from fastapi import FastAPI
from infrastructure.persistence.connection import close_pool, get_pool
from middleware.error_handler import register_error_handlers
from middleware.logging import LoggingMiddleware
from middleware.rate_limiter import RateLimiterMiddleware
from routers.analisis import router as analisis_router
from routers.errors import router as errors_router
from routers.health import router as health_router
from routers.proceso import router as proceso_router
from routers.results import router as results_router
from routers.status import router as status_router

setup_logging()


@asynccontextmanager
async def lifespan(application: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(
    title="FiscalIA - Microservicio OCI",
    description="Microservicio de IA para fiscalización del Impuesto de Industria y Comercio (ICA)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimiterMiddleware)
register_error_handlers(app)

app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(proceso_router, prefix="/api/v1", tags=["proceso"])
app.include_router(status_router, prefix="/api/v1", tags=["proceso"])
app.include_router(results_router, prefix="/api/v1", tags=["proceso"])
app.include_router(errors_router, prefix="/api/v1", tags=["proceso"])
app.include_router(analisis_router, prefix="/api/v1", tags=["analisis"])


@app.get("/")
async def root():
    return {"message": "FiscalIA - Microservicio OCI", "version": "2.0.0", "status": "running"}

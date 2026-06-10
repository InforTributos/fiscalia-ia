from config import setup_logging
from fastapi import FastAPI

from api.middleware.error_handler import register_error_handlers
from api.middleware.logging import LoggingMiddleware
from api.routers import analisis, health, score

setup_logging()

app = FastAPI(
    title="FiscalIA - Microservicio OCI",
    description="Microservicio de IA para fiscalización del Impuesto de Industria y Comercio (ICA)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(LoggingMiddleware)

register_error_handlers(app)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(analisis.router, prefix="/api/v1", tags=["analisis"])
app.include_router(score.router, prefix="/api/v1", tags=["score"])


@app.get("/")
async def root():
    return {"message": "FiscalIA - Microservicio OCI", "version": "2.0.0", "status": "running"}

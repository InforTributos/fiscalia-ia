import logging
from contextlib import asynccontextmanager

from config import settings, setup_logging
from domain.services.crosscheck_service import configurar_tarifas
from fastapi import FastAPI
from infrastructure.mcp.oracle_adapter import OracleClient, close_pool as close_oracle_pool
from infrastructure.mcp.pagination import cargar_tarifas_desde_oracle
from infrastructure.persistence.connection import close_pool, get_pool
from middleware.error_handler import register_error_handlers
from middleware.logging import LoggingMiddleware
from middleware.rate_limiter import RateLimiterMiddleware

logger = logging.getLogger(__name__)
from routers.analisis import router as analisis_router
from routers.behavioral import router as behavioral_router
from routers.entidad import router as entidad_router
from routers.errors import router as errors_router
from routers.export import router as export_router
from routers.fiscalizacion import router as fiscalizacion_router
from routers.health import router as health_router
from routers.proceso import router as proceso_router
from routers.results import router as results_router
from routers.status import router as status_router

setup_logging()


@asynccontextmanager
async def lifespan(application: FastAPI):
    await get_pool()

    # Load CIIU tarifas from Oracle at startup
    await _init_tarifas()

    from infrastructure.persistence import queries
    try:
        recovered = await queries.recuperar_procesos_interrumpidos()
        if recovered:
            logger.warning(
                "Startup: %d procesos marcados como INTERRUMPIDO (tareas huerfanas de session anterior)",
                recovered,
            )
    except Exception as e:
        logger.error("Startup: error recuperando procesos interrumpidos — %s", e)

    yield
    await close_pool()
    await close_oracle_pool()


async def _init_tarifas():
    """Load CIIU tarifas from Oracle declarations at startup."""
    try:
        client = OracleClient()
        await client.initialize()
        tarifas = await cargar_tarifas_desde_oracle(client, "2024")
        if tarifas:
            configurar_tarifas(tarifas)
            logger.info("Startup: %d tarifas CIIU cargadas desde Oracle", len(tarifas))
        else:
            logger.info("Startup: no se cargaron tarifas desde Oracle — usando defaults hardcodeados")
        await client.close()
    except Exception as e:
        logger.warning(
            "Startup: no se pudieron cargar tarifas desde Oracle (%s) — usando defaults hardcodeados",
            e,
        )


app = FastAPI(
    title=f"FiscalIA - {settings.municipio}",
    description=f"Microservicio de IA para fiscalización del ICA — {settings.municipio}, {settings.departamento}",
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
app.include_router(entidad_router, prefix="/api/v1", tags=["entidad"])
app.include_router(analisis_router, prefix="/api/v1", tags=["analisis"])
app.include_router(behavioral_router, prefix="/api/v1", tags=["comportamiento"])
app.include_router(fiscalizacion_router, prefix="/api/v1", tags=["fiscalizacion"])
app.include_router(export_router, prefix="/api/v1", tags=["export"])


@app.get("/")
async def root():
    return {"message": f"FiscalIA - {settings.municipio}", "version": "2.0.0", "status": "running"}

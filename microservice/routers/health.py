import time

from config import settings
from fastapi import APIRouter
from infrastructure.llm.llm_service import LLMService
from infrastructure.persistence.connection import verificar_conexion

router = APIRouter()


@router.get("/health")
async def health():
    pg_ok = await verificar_conexion()
    llm_service = LLMService()
    uptime = int(time.time() - settings.startup_time)
    return {
        "status": "healthy" if pg_ok else "degraded",
        "version": "2.0.0",
        "checks": {
            "postgres": "ok" if pg_ok else "error",
            "llm_providers": llm_service.provider_names,
            "llm_primary": "ok" if llm_service.providers_count > 0 else "not_configured",
        },
        "uptime_seconds": uptime,
    }

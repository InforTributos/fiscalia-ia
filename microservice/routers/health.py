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
    await llm_service.async_init()
    uptime = int(time.time() - settings.startup_time)

    nvidia = next((p for p in llm_service.providers if hasattr(p, "model")), None)
    model_name = nvidia.model if nvidia else None

    return {
        "status": "healthy" if pg_ok else "degraded",
        "version": "2.0.0",
        "checks": {
            "postgres": "ok" if pg_ok else "error",
            "llm_providers": llm_service.provider_names,
            "llm_primary": "ok" if llm_service.providers_count > 0 else "not_configured",
            "nvidia_model": model_name,
        },
        "uptime_seconds": uptime,
    }

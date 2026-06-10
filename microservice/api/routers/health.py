import time

from config import settings
from fastapi import APIRouter, Depends
from infrastructure.adapters.cache.memory_cache import MemoryCache
from infrastructure.persistence.connection import verificar_conexion

from api.deps import get_cache

router = APIRouter()


@router.get("/health")
async def health(cache: MemoryCache = Depends(get_cache)):
    oracle_ok = verificar_conexion()
    uptime = int(time.time() - settings.startup_time)
    return {
        "status": "healthy" if oracle_ok else "degraded",
        "version": "2.0.0",
        "llm_provider": f"{settings.llm_primary_provider}/{settings.llm_primary_model}",
        "llm_fallback": f"{settings.llm_fallback_provider}/{settings.llm_fallback_model}",
        "oracle_connected": oracle_ok,
        "uptime_seconds": uptime,
        "cache_size": cache.size,
        "cache_ttl": settings.cache_ttl_seconds,
    }

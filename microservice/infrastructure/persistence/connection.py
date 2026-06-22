import logging

import asyncpg
from config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        logger.info("Creando pool asyncpg para PostgreSQL")
        _pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            min_size=settings.pool_min_size,
            max_size=settings.pool_max_size,
            timeout=settings.pool_timeout,
        )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def verificar_conexion() -> bool:
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            return True
    except Exception as e:
        logger.error("Error conectando a PostgreSQL: %s", str(e))
        return False

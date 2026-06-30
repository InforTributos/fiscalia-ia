import logging
from typing import Any

import oracledb
from config import settings

logger = logging.getLogger(__name__)

_pool: oracledb.AsyncConnectionPool | None = None


class OracleClient:
    def __init__(self):
        self._pool = None

    async def initialize(self):
        global _pool
        if _pool is None:
            dsn = oracledb.makedsn(settings.oracle_host, settings.oracle_port, service_name=settings.oracle_service)
            _pool = await oracledb.create_pool_async(
                user=settings.oracle_user,
                password=settings.oracle_password,
                dsn=dsn,
                min=settings.oracle_pool_min,
                max=settings.oracle_pool_max,
                timeout=settings.oracle_pool_timeout,
            )
            logger.info("Oracle pool creado: min=%d max=%d", settings.oracle_pool_min, settings.oracle_pool_max)
        self._pool = _pool

    async def execute_sql(self, query: str, bind_params: dict[str, Any] | None = None) -> list[dict]:
        if self._pool is None:
            await self.initialize()
        async with self._pool.acquire() as conn:
            cursor = conn.cursor()
            try:
                result = await cursor.execute(query, bind_params or {})
                rows = await result.fetchall()
                columns = [c[0].lower() for c in result.description] if result.description else []
                return [dict(zip(columns, row)) for row in rows]
            finally:
                await cursor.close()

    async def execute_sql_raw(self, query: str, bind_params: dict[str, Any] | None = None) -> Any:
        if self._pool is None:
            await self.initialize()
        async with self._pool.acquire() as conn:
            cursor = conn.cursor()
            try:
                result = await cursor.execute(query, bind_params or {})
                rows = await result.fetchall()
                if not rows:
                    return None
                return rows
            finally:
                await cursor.close()

    async def close(self):
        global _pool
        if _pool:
            await _pool.close()
            _pool = None
            logger.info("Oracle pool cerrado")

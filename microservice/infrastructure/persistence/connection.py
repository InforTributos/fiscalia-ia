import logging

import oracledb
from config import settings

logger = logging.getLogger(__name__)

_pool = None
_pool_attempted = False


def get_pool():
    global _pool, _pool_attempted
    if _pool is None and not _pool_attempted:
        _pool_attempted = True
        try:
            logger.info("Creando pool de conexiones Oracle")
            _pool = oracledb.create_pool(
                user=settings.oracle_user,
                password=settings.oracle_password,
                dsn=settings.oracle_dsn,
                min=2,
                max=10,
                increment=1,
                getmode=oracledb.POOL_GETMODE_WAIT,
                timeout=5,
            )
        except Exception as e:
            logger.error("Error creando pool Oracle: %s", str(e))
            _pool = None
    return _pool


def verificar_conexion() -> bool:
    try:
        pool = get_pool()
        if pool is None:
            return False
        with pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM dual")
                return True
    except Exception as e:
        logger.error("Error conectando a Oracle: %s", str(e))
        return False

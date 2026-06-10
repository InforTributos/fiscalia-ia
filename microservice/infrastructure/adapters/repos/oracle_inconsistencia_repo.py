import logging

import oracledb
from domain.ports.inconsistencia_repo import InconsistenciaRepo
from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo

from infrastructure.persistence.connection import get_pool

logger = logging.getLogger(__name__)


class OracleInconsistenciaRepo(InconsistenciaRepo):
    def obtener_inconsistencias(self, nit: NIT, periodo: Periodo) -> list[dict]:
        pool = get_pool()
        try:
            with pool.acquire() as conn:
                with conn.cursor() as cur:
                    result = cur.callfunc(
                        "FISCAL_INC.obtener_inconsistencias",
                        oracledb.CURSOR,
                        [nit.formateado(), periodo.valor],
                    )
                    cols = [col[0].lower() for col in result.description]
                    return [dict(zip(cols, row)) for row in result]
        except Exception as e:
            logger.error("Error obteniendo inconsistencias para NIT %s: %s", nit.formateado(), str(e))
            return []

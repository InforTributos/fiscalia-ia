import logging

import oracledb
from domain.ports.analisis_repo import ScoreRepo
from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo

from infrastructure.persistence.connection import get_pool

logger = logging.getLogger(__name__)


class OracleScoreRepo(ScoreRepo):
    def obtener_srf(self, nit: NIT, periodo: Periodo) -> dict:
        pool = get_pool()
        try:
            with pool.acquire() as conn:
                with conn.cursor() as cur:
                    result = cur.callfunc(
                        "FISCAL_SCORE.obtener_srf",
                        oracledb.CURSOR,
                        [nit.formateado(), periodo.valor],
                    )
                    cols = [col[0].lower() for col in result.description]
                    row = result.fetchone()
                    return dict(zip(cols, row)) if row else {}
        except Exception as e:
            logger.error("Error obteniendo SRF para NIT %s: %s", nit.formateado(), str(e))
            return {"srf_total": 0, "comp_exogena": 0, "comp_tarifa": 0, "comp_omision": 0, "comp_rues": 0}

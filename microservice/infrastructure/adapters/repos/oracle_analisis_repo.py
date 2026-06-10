import logging

import oracledb
from domain.ports.analisis_repo import AnalisisRepo
from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo

from infrastructure.persistence.connection import get_pool

logger = logging.getLogger(__name__)


class OracleAnalisisRepo(AnalisisRepo):
    def guardar_analisis(
        self,
        nit: NIT,
        periodo: Periodo,
        prompt: str,
        respuesta_ia: str,
        tokens_entrada: int = 0,
        tokens_salida: int = 0,
    ) -> int:
        pool = get_pool()
        try:
            with pool.acquire() as conn:
                with conn.cursor() as cur:
                    result = cur.callfunc(
                        "FISCAL_ANALISIS_IA.guardar",
                        oracledb.NUMBER,
                        [
                            None,
                            "COMPLETO",
                            prompt,
                            respuesta_ia,
                            tokens_entrada,
                            tokens_salida,
                            0.0,
                            0,
                        ],
                    )
                    conn.commit()
                    return result
        except Exception as e:
            logger.error("Error guardando análisis IA: %s", str(e))
            return 0

import logging
import time
from dataclasses import dataclass

from domain.ports.analisis_repo import ScoreRepo
from domain.ports.llm_port import LLMPort
from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo
from domain.value_objects.score_riesgo import ScoreRiesgo
from infrastructure.adapters.cache.memory_cache import MemoryCache

logger = logging.getLogger(__name__)


@dataclass
class ScoreDTO:
    nit: str
    srf: float
    nivel: str
    componentes: list[dict]
    explicacion_ia: str
    tiempo_analisis_ms: int


class CalcularScore:
    def __init__(self, score_repo: ScoreRepo, llm: LLMPort, cache: MemoryCache):
        self.score_repo = score_repo
        self.llm = llm
        self.cache = cache

    async def ejecutar(self, nit_str: str, periodo_str: str) -> ScoreDTO:
        inicio = time.time()
        nit = NIT(nit_str)
        periodo = Periodo(periodo_str)

        srf_data = self.score_repo.obtener_srf(nit, periodo)
        score = ScoreRiesgo(srf_data.get("srf_total", 0))

        contexto = {
            "tipo": "explicacion_srf",
            "nit": nit.formateado(),
            "periodo": periodo.valor,
            "srf": srf_data,
        }
        cache_key = f"score:{nit_str}:{periodo_str}"
        respuesta_ia = self.cache.obtener(cache_key)
        if respuesta_ia is not None:
            logger.info("Cache hit para %s", cache_key)
        else:
            logger.info("Cache miss para %s, llamando LLM", cache_key)
            respuesta_ia = await self.llm.analizar(contexto)
            self.cache.guardar(cache_key, respuesta_ia)

        return ScoreDTO(
            nit=nit.formateado(),
            srf=score.valor,
            nivel=score.nivel,
            componentes=[
                {"nombre": "Diferencia exógena vs ICA", "valor": srf_data.get("comp_exogena", 0), "peso": 35},
                {"nombre": "Antigüedad sin declarar", "valor": srf_data.get("comp_omision", 0), "peso": 20},
                {"nombre": "Discrepancia tarifa CIIU", "valor": srf_data.get("comp_tarifa", 0), "peso": 25},
                {"nombre": "Estado RUES vs padrón", "valor": srf_data.get("comp_rues", 0), "peso": 20},
            ],
            explicacion_ia=respuesta_ia.get("explicacion", ""),
            tiempo_analisis_ms=int((time.time() - inicio) * 1000),
        )

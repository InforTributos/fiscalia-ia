import logging
import time

from domain.entities.analisis import Analisis
from domain.entities.hallazgo import Hallazgo
from domain.ports.analisis_repo import AnalisisRepo, ScoreRepo
from domain.ports.cruce_repo import CruceRepo
from domain.ports.inconsistencia_repo import InconsistenciaRepo
from domain.ports.llm_port import LLMPort
from domain.value_objects.dinero import Dinero
from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo
from domain.value_objects.score_riesgo import ScoreRiesgo
from infrastructure.adapters.cache.memory_cache import MemoryCache

from application.dto.analisis_dto import AnalisisDTO

logger = logging.getLogger(__name__)


class AnalizarContribuyente:
    def __init__(
        self,
        cruce_repo: CruceRepo,
        inconsistencia_repo: InconsistenciaRepo,
        score_repo: ScoreRepo,
        analisis_repo: AnalisisRepo,
        llm: LLMPort,
        cache: MemoryCache,
    ):
        self.cruce_repo = cruce_repo
        self.inconsistencia_repo = inconsistencia_repo
        self.score_repo = score_repo
        self.analisis_repo = analisis_repo
        self.llm = llm
        self.cache = cache

    async def ejecutar(self, nit_str: str, periodo_str: str) -> AnalisisDTO:
        inicio = time.time()
        nit = NIT(nit_str)
        periodo = Periodo(periodo_str)

        cruces = self.cruce_repo.obtener_cruces(nit, periodo)
        inconsistencias = self.inconsistencia_repo.obtener_inconsistencias(nit, periodo)
        srf_data = self.score_repo.obtener_srf(nit, periodo)

        contexto = {
            "tipo": "analisis_completo",
            "nit": nit.formateado(),
            "periodo": periodo.valor,
            "cruces": cruces,
            "inconsistencias": inconsistencias,
            "srf": srf_data,
        }
        cache_key = f"analisis:{nit_str}:{periodo_str}"
        cache_hit = False
        respuesta_ia = self.cache.obtener(cache_key)
        if respuesta_ia is not None:
            cache_hit = True
            logger.info("Cache hit para %s", cache_key)
        else:
            logger.info("Cache miss para %s, llamando LLM", cache_key)
            respuesta_ia = await self.llm.analizar(contexto)
            self.cache.guardar(cache_key, respuesta_ia)

        srf_total = srf_data.get("srf_total", 0)
        score = ScoreRiesgo(srf_total)
        hallazgos = self._mapear_hallazgos(inconsistencias, respuesta_ia.get("hallazgos_enriquecidos", []))

        analisis = Analisis(
            nit=nit,
            periodo=periodo,
            score=score,
            hallazgos=hallazgos,
            explicacion_srf=respuesta_ia.get("explicacion", ""),
            cache_hit=cache_hit,
            modo_degradado=respuesta_ia.get("modo_degradado", False),
        )

        self.analisis_repo.guardar_analisis(
            nit=nit,
            periodo=periodo,
            prompt=str(contexto),
            respuesta_ia=str(respuesta_ia),
            tokens_entrada=respuesta_ia.get("tokens_entrada", 0),
            tokens_salida=respuesta_ia.get("tokens_salida", 0),
        )

        return self._to_dto(nit, periodo, analisis, inicio)

    def _mapear_hallazgos(self, inconsistencias: list[dict], enriquecidos: list[dict]) -> list[Hallazgo]:
        hallazgos = []
        for inc in inconsistencias:
            hallazgos.append(
                Hallazgo(
                    tipo=inc.get("tipo_incidencia", "DESCONOCIDO"),
                    severidad=inc.get("severidad", "MEDIA"),
                    descripcion=inc.get("descripcion", ""),
                    diferencia=Dinero(inc.get("diferencia", 0)) if inc.get("diferencia") else None,
                    declarado=Dinero(inc.get("valor_declarado", 0)) if inc.get("valor_declarado") else None,
                    referencia=Dinero(inc.get("valor_referencia", 0)) if inc.get("valor_referencia") else None,
                    ciiu=inc.get("ciiu"),
                )
            )
        return hallazgos

    def _to_dto(self, nit: NIT, periodo: Periodo, analisis: Analisis, inicio: float) -> AnalisisDTO:
        return AnalisisDTO(
            nit=nit.formateado(),
            periodo=periodo.valor,
            score_riesgo=analisis.score.valor,
            nivel_riesgo=analisis.score.nivel,
            hallazgos=[
                {
                    "tipo": h.tipo,
                    "severidad": h.severidad,
                    "descripcion": h.descripcion,
                    "diferencia": h.diferencia.valor if h.diferencia else None,
                    "ciiu": h.ciiu,
                }
                for h in analisis.hallazgos
            ],
            explicacion_srf=analisis.explicacion_srf,
            tiempo_analisis_ms=int((time.time() - inicio) * 1000),
            cache_hit=analisis.cache_hit,
            modo_degradado=analisis.modo_degradado,
        )

import json
import logging
import uuid

from domain.services.crosscheck_service import (
    calcular_srf,
    clasificar_por_datos,
    extraer_inconsistencias,
)
from domain.services.inconsistency_service import nivel_riesgo
from infrastructure.llm.llm_service import LLMService
from infrastructure.llm.prompts import construir_prompt
from infrastructure.mcp.oracle_adapter import OracleClient
from infrastructure.mcp.pagination import obtener_datos_fiscales
from infrastructure.persistence.repositorio_proceso import PostgresProcesoRepo

logger = logging.getLogger(__name__)


class ProcesoOrchestrator:
    def __init__(self, llm_service: LLMService | None = None, proceso_repo: PostgresProcesoRepo | None = None):
        self.llm = llm_service or LLMService()
        self.proceso_repo = proceso_repo or PostgresProcesoRepo()

    async def ejecutar(
        self, proceso_id: str, intento_id: int, nit: str, detalle_id: int,
        periodo: str = "2024", datos: dict | None = None,
    ):
        logger.info("Orquestador: analizando NIT %s (detalle %d, periodo %s)", nit, detalle_id, periodo)

        try:
            if not datos:
                client = OracleClient()
                datos = await obtener_datos_fiscales(client, nit, periodo)
            if not datos:
                logger.warning("NIT %s sin datos fiscales disponibles", nit)
                return

            clasificacion = clasificar_por_datos(datos)

            if clasificacion == "OMISO":
                await self._procesar_omiso(detalle_id, datos)
            elif clasificacion == "INEXACTO":
                await self._procesar_inexacto(detalle_id, datos)
            else:
                logger.info("NIT %s clasificado como EXACTO — sin análisis IA", nit)

        except Exception as e:
            logger.error("Error analizando NIT %s: %s", nit, str(e))
            await self.proceso_repo.insertar_error_detalle(
                uuid.UUID(proceso_id), detalle_id, nit, "PROCESO", "ORCHESTRATION_FAIL", str(e),
            )

    async def _procesar_omiso(self, detalle_id: int, datos: dict):
        srf_data = calcular_srf(datos)
        resultado = await self._invocar_llm("omiso", datos, [], srf_data["srf_total"])

        await self.proceso_repo.actualizar_resultado_detalle(
            id=detalle_id,
            srf_total=srf_data["srf_total"],
            nivel_riesgo="ALTO",
            hallazgos=[{"tipo": "OMISION", "explicacion_ia": resultado["explicacion"]}],
            explicacion_ia=resultado["explicacion"],
            tokens_entrada=resultado["tokens_entrada"],
            tokens_salida=resultado["tokens_salida"],
            costo_estimado=resultado["costo_estimado"],
            mcp_score=srf_data["srf_total"],
        )

    async def _procesar_inexacto(self, detalle_id: int, datos: dict):
        inconsistencias = extraer_inconsistencias(datos)
        srf_data = calcular_srf(datos)

        resultado = await self._invocar_llm("inexacto", datos, inconsistencias, srf_data["srf_total"])
        nivel = nivel_riesgo(srf_data["srf_total"])

        await self.proceso_repo.actualizar_resultado_detalle(
            id=detalle_id,
            srf_total=srf_data["srf_total"],
            nivel_riesgo=nivel,
            hallazgos=inconsistencias,
            explicacion_ia=resultado["explicacion"],
            tokens_entrada=resultado["tokens_entrada"],
            tokens_salida=resultado["tokens_salida"],
            costo_estimado=resultado["costo_estimado"],
            mcp_score=srf_data["srf_total"],
        )

    async def _invocar_llm(self, tipo: str, datos: dict, inconsistencias: list, srf_total: float) -> dict:
        try:
            messages = [
                {"role": "system", "content": "Eres un asistente experto en fiscalización del ICA en Colombia."},
                {"role": "user", "content": construir_prompt(
                    tipo,
                    datos_fiscales=json.dumps(datos, indent=2, ensure_ascii=False),
                    inconsistencias=json.dumps(inconsistencias, indent=2, ensure_ascii=False),
                    srf_total=str(srf_total),
                )},
            ]
            resultado = await self.llm.analyze(messages)
            return {
                "explicacion": resultado.get("explicacion", resultado.get("respuesta_plana", "")),
                "tokens_entrada": resultado.get("tokens_entrada", 0),
                "tokens_salida": resultado.get("tokens_salida", 0),
                "costo_estimado": resultado.get("costo_estimado", 0.0),
            }
        except Exception as e:
            logger.warning("Error invocando LLM para %s: %s", tipo, str(e))
            return {
                "explicacion": "Análisis no disponible por error en LLM.",
                "tokens_entrada": 0,
                "tokens_salida": 0,
                "costo_estimado": 0.0,
            }

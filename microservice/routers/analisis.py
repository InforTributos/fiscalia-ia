import json
import logging
import time

from cache import get_cache
from domain.errors import NITNoEncontradoError
from domain.services.crosscheck_service import calcular_srf, clasificar_por_datos, extraer_inconsistencias
from domain.services.inconsistency_service import nivel_riesgo
from fastapi import APIRouter
from infrastructure.llm.llm_service import LLMService
from infrastructure.llm.prompts import construir_prompt
from infrastructure.mcp.oracle_adapter import OracleClient
from infrastructure.mcp.pagination import obtener_datos_fiscales
from schemas.contribuyente import (
    AnalyzeResponse,
    ComponenteSRF,
    HallazgoContribuyente,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analizar/{contribuyente_nit}", response_model=AnalyzeResponse)
async def analizar_contribuyente(
    contribuyente_nit: str,
    periodo: str = "2024",
):
    inicio = time.time()
    cache = get_cache()
    cache_key = f"analisis:{contribuyente_nit}:{periodo}"

    cached = cache.obtener(cache_key)
    if cached is not None:
        cached["cache_hit"] = True
        return AnalyzeResponse(**cached)

    client = OracleClient()
    datos = await obtener_datos_fiscales(client, contribuyente_nit, periodo)
    if not datos:
        raise NITNoEncontradoError(contribuyente_nit)

    clasificacion = clasificar_por_datos(datos)
    inconsistencias = extraer_inconsistencias(datos)
    srf_data = calcular_srf(datos)
    srf_total = srf_data["srf_total"]

    llm = LLMService()
    explicacion_ia = ""
    tokens_in = 0
    tokens_out = 0
    provider = ""
    try:
        messages = [
            {"role": "system", "content": "Eres un asistente experto en fiscalización del ICA en Colombia."},
            {"role": "user", "content": construir_prompt(
                "omiso" if clasificacion == "OMISO" else "inexacto",
                datos_fiscales=json.dumps(datos, indent=2, ensure_ascii=False),
                inconsistencias=json.dumps(inconsistencias, indent=2, ensure_ascii=False),
                srf_total=str(srf_total),
            )},
        ]
        resultado_llm = await llm.analyze(messages)
        explicacion_ia = resultado_llm.get("explicacion", resultado_llm.get("respuesta_plana", ""))
        tokens_in = resultado_llm.get("tokens_entrada", 0)
        tokens_out = resultado_llm.get("tokens_salida", 0)
        provider = resultado_llm.get("provider", "")
    except Exception as e:
        logger.warning("Error invocando LLM para NIT %s: %s", contribuyente_nit, str(e))

    duracion_ms = int((time.time() - inicio) * 1000)
    nivel = nivel_riesgo(srf_total)
    hallazgos_dto = [
        HallazgoContribuyente(**h) if isinstance(h, dict) else HallazgoContribuyente(tipo=str(h))
        for h in inconsistencias
    ]

    response = AnalyzeResponse(
        contribuyente_nit=contribuyente_nit,
        razon_social=datos.get("razon_social", ""),
        ciiu=datos.get("ciiu", ""),
        clasificacion=clasificacion,
        mcp_score=srf_total,
        mcp_razon="",
        srf_total=srf_total,
        componentes_srf=[
            ComponenteSRF(nombre=comp.get("nombre", ""), valor=comp.get("valor", 0), peso=comp.get("peso", 0))
            for comp in srf_data.get("componentes", {}).values()
        ],
        nivel_riesgo=nivel,
        hallazgos=hallazgos_dto,
        explicacion_ia=explicacion_ia,
        tokens_utilizados=tokens_in + tokens_out,
        duracion_ms=duracion_ms,
        provider_utilizado=provider,
        cache_hit=False,
    )

    cache.guardar(cache_key, response.model_dump())
    return response

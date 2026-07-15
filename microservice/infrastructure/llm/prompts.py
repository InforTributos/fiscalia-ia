import json
import logging

from config import settings

logger = logging.getLogger(__name__)

_MUNICIPIO = settings.municipio

PROMPT_ANALISIS_OMISO = """
Eres un experto en fiscalización tributaria municipal de {municipio}, Colombia.
Analiza el siguiente contribuyente OMISO en el pago del Impuesto de Industria y Comercio (ICA).

Datos del contribuyente:
{datos_fiscales}

Genera un JSON con la siguiente estructura:
{{
    "brecha_fiscal_estimada": float,
    "explicacion": "string — explicación en lenguaje natural para el fiscalizador (máx 3 párrafos)",
    "recomendacion": "string — acción sugerida para el fiscalizador"
}}
"""

PROMPT_ANALISIS_INEXACTO = """
Eres un experto en fiscalización tributaria municipal de {municipio}, Colombia.
Analiza las siguientes INCONSISTENCIAS en la declaración de ICA de un contribuyente.

Datos del contribuyente:
{datos_fiscales}

Inconsistencias detectadas:
{inconsistencias}

Score de Riesgo Fiscal: {srf_total}/100

Genera un JSON con la siguiente estructura:
{{
    "hallazgos": [
        {{
            "tipo": "string — SUBDECLARACION_EXOGENA | OMISION | TARIFA_INCORRECTA | BASE_CERO | OTRO",
            "severidad": "ALTA | MEDIA | BAJA",
            "declarado_ica": float | null,
            "exogena": float | null,
            "diferencia": float | null,
            "variacion_pct": float | null,
            "explicacion_ia": "string — explicación en lenguaje natural",
            "recomendacion": "string — acción sugerida"
        }}
    ],
    "srf_total": float,
    "nivel_riesgo": "ALTO | MEDIO | BAJO",
    "explicacion_ia": "string — resumen ejecutivo del análisis"
}}
"""

PROMPT_SRF_EXPLICACION = """
Eres un asistente de fiscalización del ICA en {municipio}, Colombia.
Explica en lenguaje simple por qué este contribuyente tiene un Score de Riesgo Fiscal de {srf_total}/100.

Factores del SRF:
{factores}

Genera un JSON con:
{{
    "explicacion": "string — explicación para el fiscalizador (máx 2 párrafos)",
    "top_factores": ["string", "string", "string"]
}}
"""

PROMPT_CLASIFICACION = """
Eres un clasificador de contribuyentes para fiscalización del ICA en {municipio}, Colombia.
Basado en los datos del MCP, clasifica el siguiente contribuyente.

Datos MCP:
{datos_mcp}

Genera un JSON con:
{{
    "clasificacion": "OMISO | EXACTO | INEXACTO",
    "razon": "string — razón de la clasificación",
    "confianza": float  # 0.0 a 1.0
}}
"""


PROMPT_RESUMEN_CAMPANA = """
Eres un experto en fiscalización tributaria municipal de {municipio}, Colombia.
Genera un resumen ejecutivo de la campaña de fiscalización del ICA.

Parámetros de la campaña:
- Periodo: {periodo}
- Actividad económica (CIIU): {actividad_economica}
- Total candidatos analizados: {total_candidatos}
- Omisos: {total_omisos}
- Inexactos: {total_inexactos}

Estadísticas de hallazgos:
{estadisticas_hallazgos}

Top 10 contribuyentes por score de riesgo:
{top_contribuyentes}

Patrones temporales detectados:
{patrones_temporales}

Genera un JSON con:
{{
    "resumen_ejecutivo": "string — resumen de 3-5 párrafos para el director de fiscalización",
    "hallazgos_principales": ["string", "string", "string"],
    "brecha_fiscal_total_estimada": float,
    "recomendaciones": ["string", "string", "string"],
    "distribucion_riesgo": {{
        "critico": int,
        "alto": int,
        "medio": int,
        "bajo": int
    }}
}}
"""


def construir_prompt(tipo: str, **kwargs) -> str:
    kwargs.setdefault("municipio", _MUNICIPIO)
    if tipo == "omiso":
        return PROMPT_ANALISIS_OMISO.format(**kwargs)
    elif tipo == "inexacto":
        return PROMPT_ANALISIS_INEXACTO.format(**kwargs)
    elif tipo == "srf":
        return PROMPT_SRF_EXPLICACION.format(**kwargs)
    elif tipo == "clasificacion":
        return PROMPT_CLASIFICACION.format(**kwargs)
    elif tipo == "resumen_campana":
        return PROMPT_RESUMEN_CAMPANA.format(**kwargs)
    return json.dumps(kwargs, indent=2, ensure_ascii=False)


def parsear_respuesta(texto: str) -> dict:
    try:
        inicio = texto.index("{")
        fin = texto.rindex("}") + 1
        return json.loads(texto[inicio:fin])
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning("Error parseando respuesta LLM: %s", str(e))
        return {"explicacion": texto, "hallazgos_enriquecidos": []}

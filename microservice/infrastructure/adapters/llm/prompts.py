import json
import logging

logger = logging.getLogger(__name__)


class Prompts:
    def construir(self, contexto: dict) -> str:
        tipo = contexto.get("tipo")

        if tipo == "analisis_completo":
            return self._prompt_analisis(contexto)
        elif tipo == "explicacion_srf":
            return self._prompt_score(contexto)
        return self._prompt_generico(contexto)

    def _prompt_analisis(self, ctx: dict) -> str:
        return f"""
Eres un asistente de fiscalización del Impuesto de Industria y Comercio (ICA) en Valledupar, Colombia.

CONTRIBUYENTE:
NIT: {ctx.get('nit')}
Período: {ctx.get('periodo')}

RESULTADOS CRUCE EXÓGENA VS DECLARADO:
{json.dumps(ctx.get('cruces', []), indent=2, ensure_ascii=False)}

INCONSISTENCIAS DETECTADAS:
{json.dumps(ctx.get('inconsistencias', []), indent=2, ensure_ascii=False)}

SCORE DE RIESGO FISCAL:
{json.dumps(ctx.get('srf', {}), indent=2, ensure_ascii=False)}

Genera un análisis JSON con:
1. "explicacion": explicación del SRF y los factores de mayor riesgo (máx 3 párrafos)
2. "hallazgos_enriquecidos": array con cada hallazgo incluyendo explicación en lenguaje natural y recomendación de acción
"""

    def _prompt_score(self, ctx: dict) -> str:
        return f"""
Eres un asistente de fiscalización del ICA en Valledupar, Colombia.

CONTRIBUYENTE:
NIT: {ctx.get('nit')}
Período: {ctx.get('periodo')}

SCORE DE RIESGO FISCAL:
{json.dumps(ctx.get('srf', {}), indent=2, ensure_ascii=False)}

Genera un JSON con:
1. "explicacion": explica el SRF en lenguaje natural para el funcionario fiscalizador, mencionando los 3 factores de mayor peso y su significado (máx 2 párrafos)
"""

    def _prompt_generico(self, ctx: dict) -> str:
        return f"Contexto: {json.dumps(ctx, indent=2, ensure_ascii=False)}\n\nGenera un análisis en JSON."

    def parsear_respuesta(self, texto: str) -> dict:
        try:
            inicio = texto.index("{")
            fin = texto.rindex("}") + 1
            return json.loads(texto[inicio:fin])
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("Error parseando respuesta LLM: %s", str(e))
            return {"explicacion": texto, "hallazgos_enriquecidos": []}

from __future__ import annotations

import json
import uuid

from application.use_cases.gestionar_hallazgos import GestionarHallazgosUseCase
from domain.fiscalizacion.agent_reviewer import fusionar_revision_ia, revisar_hallazgo_deterministico
from infrastructure.llm.llm_service import LLMService
from infrastructure.persistence import hallazgos_queries


class RevisarHallazgoAgenteUseCase:
    async def revisar(self, hallazgo_id: uuid.UUID, usar_ia: bool = True) -> dict:
        hallazgo = await GestionarHallazgosUseCase().obtener(hallazgo_id)
        base = revisar_hallazgo_deterministico(hallazgo)
        tokens_entrada = 0
        tokens_salida = 0
        modo_degradado = False

        resultado = base
        if usar_ia:
            ia = await self._revisar_con_ia(hallazgo, base)
            tokens_entrada = int(ia.get("tokens_entrada") or 0)
            tokens_salida = int(ia.get("tokens_salida") or 0)
            modo_degradado = bool(ia.get("modo_degradado"))
            resultado = fusionar_revision_ia(base, ia)

        row = await hallazgos_queries.registrar_revision_agente(
            hallazgo_id=hallazgo_id,
            agente=base["agente"],
            version=base["version"],
            resultado=resultado,
            modo_degradado=modo_degradado,
            tokens_entrada=tokens_entrada,
            tokens_salida=tokens_salida,
        )
        return row

    async def _revisar_con_ia(self, hallazgo: dict, base: dict) -> dict:
        messages = [
            {
                "role": "system",
                "content": (
                    "Eres un agente revisor adversarial de hallazgos de fiscalizacion ICA. "
                    "No decides el caso; solo identificas riesgos, evidencia faltante y preguntas. "
                    "Responde JSON estricto."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "hallazgo": _compactar_hallazgo(hallazgo),
                    "revision_deterministica": base,
                    "instrucciones": {
                        "objetivo": "evaluar calidad probatoria antes de revision humana",
                        "salida": ["comentario", "riesgos", "preguntas"],
                    },
                }, ensure_ascii=False),
            },
        ]
        schema = {
            "type": "object",
            "properties": {
                "comentario": {"type": "string"},
                "riesgos": {"type": "array", "items": {"type": "string"}},
                "preguntas": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["comentario", "riesgos", "preguntas"],
        }
        return await LLMService().analyze(messages, schema=schema)


def _compactar_hallazgo(hallazgo: dict) -> dict:
    return {
        "contribuyente_nit": hallazgo.get("contribuyente_nit"),
        "regla": hallazgo.get("regla"),
        "periodo": hallazgo.get("periodo"),
        "tipo_hallazgo": hallazgo.get("tipo_hallazgo"),
        "fuerza_probatoria": hallazgo.get("fuerza_probatoria"),
        "brecha_valor": hallazgo.get("brecha_valor"),
        "impuesto_estimado": hallazgo.get("impuesto_estimado"),
        "score": hallazgo.get("score"),
        "accionable": hallazgo.get("accionable"),
        "estado": hallazgo.get("estado"),
        "resumen": hallazgo.get("resumen"),
        "evidencias": hallazgo.get("evidencias", [])[:5],
    }


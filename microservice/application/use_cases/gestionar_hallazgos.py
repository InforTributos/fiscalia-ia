from __future__ import annotations

import uuid
from datetime import date

from application.use_cases.generar_expediente_fiscal import GenerarExpedienteFiscalUseCase
from domain.errors import HallazgoNoEncontradoError, SolicitudInvalidaError
from domain.fiscalizacion.legal_window import calcular_ventana_legal, es_omiso
from domain.fiscalizacion.rules_catalog import obtener_regla
from domain.fiscalizacion.scoring import calcular_score_hallazgo
from infrastructure.persistence import hallazgos_queries


class GestionarHallazgosUseCase:
    async def crear_hallazgo(self, payload: dict) -> dict:
        try:
            regla = obtener_regla(payload["regla"])
        except ValueError as exc:
            raise SolicitudInvalidaError(str(exc)) from exc
        tipo_hallazgo = payload.get("tipo_hallazgo") or regla.detecta
        fuerza = payload.get("fuerza_probatoria") or regla.fuerza_probatoria
        ventana = calcular_ventana_legal(payload["periodo"])
        omiso = es_omiso(tipo_hallazgo)
        dias = ventana.dias_restantes(date.today(), omiso)
        scoring = calcular_score_hallazgo(
            fuerza_probatoria=fuerza,
            impuesto_estimado=float(payload.get("impuesto_estimado") or 0),
            dias_restantes=dias,
            reincidencia=int(payload.get("reincidencia") or 0),
            corroboracion=int(payload.get("corroboracion") or 1),
        )
        accionable = ventana.es_accionable(date.today(), omiso)
        data = {
            "contribuyente_nit": payload["contribuyente_nit"],
            "regla": regla.codigo,
            "periodo": payload["periodo"],
            "tipo_hallazgo": tipo_hallazgo,
            "fuerza_probatoria": fuerza,
            "brecha_valor": payload.get("brecha_valor", 0),
            "impuesto_estimado": payload.get("impuesto_estimado", 0),
            "score": scoring["score"],
            "score_componentes": {**scoring["componentes"], "banda": scoring["banda"]},
            "ventana_limite": ventana.limite_para(omiso),
            "accionable": accionable,
            "estado": "DETECTADO" if accionable else "NO_ACCIONABLE",
            "resumen": payload.get("resumen") or regla.descripcion,
            "metadata": payload.get("metadata", {}),
        }
        if payload.get("proceso_id") and payload.get("entidad_id"):
            data["proceso_id"] = payload["proceso_id"]
            data["entidad_id"] = payload["entidad_id"]
        return await hallazgos_queries.crear_hallazgo(data, payload.get("evidencias") or [])

    async def crear_desde_grafo(self, contribuyente_nit: str, periodo: str, min_pares: int = 10) -> dict:
        expediente = await GenerarExpedienteFiscalUseCase().generar(contribuyente_nit=contribuyente_nit, periodo=periodo, min_pares=min_pares)
        analisis = expediente.get("analisis_comportamental") or {}
        metricas = analisis.get("metricas") or {}
        brecha = max((metricas.get("ingresos_exogena") or 0) - (metricas.get("base_gravable") or 0), 0)
        payload = {
            "contribuyente_nit": contribuyente_nit,
            "regla": "R8",
            "periodo": periodo,
            "tipo_hallazgo": "INEXACTO_INDICIARIO",
            "brecha_valor": brecha,
            "impuesto_estimado": 0,
            "corroboracion": 2 if expediente["grafo"]["resumen_red"].get("bonus_red", 0) > 0 else 1,
            "resumen": expediente["resumen_ejecutivo"],
            "metadata": {
                "score_fiscal_unificado": expediente["score"],
                "origen": "GRAFO_RIESGO",
            },
            "evidencias": [
                {
                    "fuente": "EXPEDIENTE_FISCAL",
                    "referencia_registro": f"{contribuyente_nit}:{periodo}",
                    "descripcion": "Expediente fiscal automatico generado desde grafo y comportamiento.",
                    "snapshot": expediente,
                }
            ],
        }
        return await self.crear_hallazgo(payload)

    async def obtener(self, hallazgo_id: uuid.UUID) -> dict:
        hallazgo = await hallazgos_queries.obtener_hallazgo(hallazgo_id)
        if not hallazgo:
            raise HallazgoNoEncontradoError(str(hallazgo_id))
        return hallazgo

    async def listar(self, **filtros):
        return await hallazgos_queries.listar_hallazgos(**filtros)

    async def revisar(self, hallazgo_id: uuid.UUID, funcionario_id: str, decision: str, motivo: str | None):
        hallazgo = await hallazgos_queries.registrar_revision(hallazgo_id, funcionario_id, decision, motivo)
        if not hallazgo:
            raise HallazgoNoEncontradoError(str(hallazgo_id))
        return hallazgo

    async def listar_revisiones_agente(self, hallazgo_id: uuid.UUID, limit: int = 10, offset: int = 0):
        return await hallazgos_queries.listar_revisiones_agente(hallazgo_id, limit, offset)

from __future__ import annotations

import json
import uuid

from infrastructure.persistence.connection import get_pool


async def crear_hallazgo(data: dict, evidencias: list[dict]) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO hallazgos_fiscales (
                    nit, regla, periodo, tipo_hallazgo, fuerza_probatoria,
                    brecha_valor, impuesto_estimado, score, score_componentes,
                    ventana_limite, accionable, estado, resumen, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11, $12, $13, $14::jsonb)
                RETURNING *
                """,
                data["nit"], data["regla"], data["periodo"], data["tipo_hallazgo"], data["fuerza_probatoria"],
                data.get("brecha_valor", 0), data.get("impuesto_estimado", 0), data["score"],
                json.dumps(data.get("score_componentes", {})), data["ventana_limite"], data["accionable"],
                data.get("estado", "DETECTADO"), data.get("resumen"), json.dumps(data.get("metadata", {})),
            )
            hallazgo = dict(row)
            for evidencia in evidencias:
                await conn.execute(
                    """
                    INSERT INTO hallazgo_evidencias (
                        hallazgo_id, fuente, referencia_registro, descripcion, snapshot
                    )
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    """,
                    hallazgo["id"], evidencia["fuente"], evidencia.get("referencia_registro"),
                    evidencia["descripcion"], json.dumps(evidencia.get("snapshot", {})),
                )
            return _normalizar_hallazgo(hallazgo)


async def obtener_hallazgo(hallazgo_id: uuid.UUID) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM hallazgos_fiscales WHERE id = $1", hallazgo_id)
        if not row:
            return None
        evidencias = await conn.fetch(
            "SELECT * FROM hallazgo_evidencias WHERE hallazgo_id = $1 ORDER BY created_at ASC",
            hallazgo_id,
        )
        revisiones = await conn.fetch(
            "SELECT * FROM hallazgo_revisiones WHERE hallazgo_id = $1 ORDER BY created_at DESC",
            hallazgo_id,
        )
        revisiones_agente = await conn.fetch(
            "SELECT * FROM hallazgo_revisiones_agente WHERE hallazgo_id = $1 ORDER BY created_at DESC",
            hallazgo_id,
        )
        result = _normalizar_hallazgo(dict(row))
        result["evidencias"] = [_normalizar_json(dict(e), ("snapshot",)) for e in evidencias]
        result["revisiones"] = [dict(r) for r in revisiones]
        result["revisiones_agente"] = [_normalizar_json(dict(r), ("resultado",)) for r in revisiones_agente]
        return result


async def listar_hallazgos(
    estado: str | None = None,
    regla: str | None = None,
    nit: str | None = None,
    accionable: bool | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[int, list[dict]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        where = ["1=1"]
        params = []
        idx = 1
        for field, value in (("estado", estado), ("regla", regla), ("nit", nit), ("accionable", accionable)):
            if value is not None:
                where.append(f"{field} = ${idx}")
                params.append(value)
                idx += 1
        offset = (page - 1) * page_size
        count = await conn.fetchval(f"SELECT COUNT(*) FROM hallazgos_fiscales WHERE {' AND '.join(where)}", *params)
        rows = await conn.fetch(
            f"""
            SELECT * FROM hallazgos_fiscales
            WHERE {' AND '.join(where)}
            ORDER BY accionable DESC, score DESC, created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params, page_size, offset,
        )
        return count or 0, [_normalizar_hallazgo(dict(r)) for r in rows]


async def registrar_revision(hallazgo_id: uuid.UUID, funcionario_id: str, decision: str, motivo: str | None) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            exists = await conn.fetchrow("SELECT * FROM hallazgos_fiscales WHERE id = $1", hallazgo_id)
            if not exists:
                return None
            await conn.execute(
                """
                INSERT INTO hallazgo_revisiones (hallazgo_id, funcionario_id, decision, motivo)
                VALUES ($1, $2, $3, $4)
                """,
                hallazgo_id, funcionario_id, decision, motivo,
            )
            estado = _estado_por_decision(decision)
            await conn.execute(
                "UPDATE hallazgos_fiscales SET estado = $1, updated_at = NOW() WHERE id = $2",
                estado, hallazgo_id,
            )
    return await obtener_hallazgo(hallazgo_id)


async def registrar_revision_agente(
    hallazgo_id: uuid.UUID,
    agente: str,
    version: str,
    resultado: dict,
    modo_degradado: bool,
    tokens_entrada: int = 0,
    tokens_salida: int = 0,
) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO hallazgo_revisiones_agente (
                hallazgo_id, agente, version, resultado, modo_degradado, tokens_entrada, tokens_salida
            )
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)
            RETURNING *
            """,
            hallazgo_id, agente, version, json.dumps(resultado), modo_degradado, tokens_entrada, tokens_salida,
        )
        return _normalizar_json(dict(row), ("resultado",))


async def listar_revisiones_agente(
    hallazgo_id: uuid.UUID,
    limit: int = 10,
    offset: int = 0,
) -> tuple[int, list[dict]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM hallazgo_revisiones_agente WHERE hallazgo_id = $1", hallazgo_id,
        )
        rows = await conn.fetch(
            """
            SELECT * FROM hallazgo_revisiones_agente
            WHERE hallazgo_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            hallazgo_id, limit, offset,
        )
        return count or 0, [_normalizar_json(dict(r), ("resultado",)) for r in rows]


def _estado_por_decision(decision: str) -> str:
    return {
        "VALIDAR": "VALIDADO",
        "DESCARTAR": "DESCARTADO",
        "PEDIR_INFO": "SOLICITA_MAS_INFO",
        "TRASLADAR": "TRASLADADO_A_PROCESO",
    }.get(decision.upper(), "EN_REVISION")


def _normalizar_hallazgo(row: dict) -> dict:
    row = _normalizar_json(row, ("score_componentes", "metadata"))
    row.setdefault("evidencias", [])
    row.setdefault("revisiones", [])
    return row


def _normalizar_json(row: dict, fields: tuple[str, ...]) -> dict:
    for field in fields:
        value = row.get(field)
        if isinstance(value, str):
            row[field] = json.loads(value)
    return row

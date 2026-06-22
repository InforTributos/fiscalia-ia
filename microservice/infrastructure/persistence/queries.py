import json
import uuid

import asyncpg
from .connection import get_pool


async def crear_cliente(nit: str, razon_social: str, email: str | None = None) -> uuid.UUID | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO clientes (nit, razon_social, email)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            nit, razon_social, email,
        )
        return row["id"] if row else None


async def obtener_cliente_por_nit(nit: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM clientes WHERE nit = $1 AND activo = TRUE", nit)
        return dict(row) if row else None


async def crear_proceso(cliente_id: uuid.UUID, nombre: str, criteria: dict) -> uuid.UUID | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO procesos (cliente_id, nombre, estado, criteria)
            VALUES ($1, $2, 'PENDIENTE', $3::jsonb)
            RETURNING id
            """,
            cliente_id, nombre, json.dumps(criteria),
        )
        return row["id"] if row else None


async def obtener_proceso_por_criteria(cliente_id: uuid.UUID, criteria: dict) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM procesos
            WHERE cliente_id = $1 AND criteria::text = $2::text
            ORDER BY created_at DESC LIMIT 1
            """,
            cliente_id, json.dumps(criteria),
        )
        return dict(row) if row else None


async def obtener_proceso(id: uuid.UUID) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM procesos WHERE id = $1", id)
        return dict(row) if row else None


async def crear_intento(proceso_id: uuid.UUID, numero: int = 1) -> int | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO proceso_intentos (proceso_id, numero_intento, estado)
            VALUES ($1, $2, 'EN_PROCESO')
            RETURNING id
            """,
            proceso_id, numero,
        )
        return row["id"] if row else None


async def obtener_intento(id: int) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM proceso_intentos WHERE id = $1", id)
        return dict(row) if row else None


async def obtener_ultimo_intento(proceso_id: uuid.UUID) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM proceso_intentos WHERE proceso_id = $1 ORDER BY numero_intento DESC LIMIT 1",
            proceso_id,
        )
        return dict(row) if row else None


async def actualizar_estado_intento(id: int, estado: str, error_resumen: str | None = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if estado in ("COMPLETADO", "ERROR"):
            await conn.execute(
                "UPDATE proceso_intentos SET estado = $1, completed_at = NOW(), error_resumen = $2 WHERE id = $3",
                estado, error_resumen, id,
            )
        else:
            await conn.execute(
                "UPDATE proceso_intentos SET estado = $1 WHERE id = $2",
                estado, id,
            )


async def actualizar_progreso_intento(id: int, procesados: int, errores_count: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE proceso_intentos SET procesados = $1, errores_count = $2 WHERE id = $3",
            procesados, errores_count, id,
        )


async def insertar_detalle(
    proceso_id: uuid.UUID, intento_id: int, nit: str,
    clasificacion: str, pagina: int = 0,
    razon_social: str | None = None, ciiu: str | None = None,
    mcp_score: float | None = None, es_candidato: bool = True,
    mcp_razon: str | None = None,
) -> int | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO proceso_detalle (proceso_id, intento_id, nit, razon_social, ciiu,
                mcp_score, es_candidato, mcp_razon, clasificacion, pagina)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
            """,
            proceso_id, intento_id, nit, razon_social, ciiu,
            mcp_score, es_candidato, mcp_razon, clasificacion, pagina,
        )
        return row["id"] if row else None


async def actualizar_resultado_detalle(
    id: int, srf_total: float | None,
    nivel_riesgo: str | None, hallazgos: list | None,
    explicacion_ia: str | None, tokens_entrada: int = 0,
    tokens_salida: int = 0, costo_estimado: float | None = None,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE proceso_detalle
            SET srf_total = $1, nivel_riesgo = $2, hallazgos = $3::jsonb,
                explicacion_ia = $4, tokens_entrada = $5, tokens_salida = $6,
                costo_estimado = $7
            WHERE id = $8
            """,
            srf_total, nivel_riesgo,
            json.dumps(hallazgos) if hallazgos else None,
            explicacion_ia, tokens_entrada, tokens_salida, costo_estimado, id,
        )


async def insertar_error_proceso(proceso_id: uuid.UUID, intento_id: int, capa: str, codigo: str, mensaje: str, contexto: dict | None = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO proceso_errores (proceso_id, intento_id, capa, codigo, mensaje, contexto)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            """,
            proceso_id, intento_id, capa, codigo, mensaje, json.dumps(contexto) if contexto else None,
        )


async def insertar_error_detalle(detalle_id: int, nit: str, capa: str, codigo: str, mensaje: str, contexto: dict | None = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO proceso_detalle_errores (detalle_id, nit, capa, codigo, mensaje, contexto)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            """,
            detalle_id, nit, capa, codigo, mensaje, json.dumps(contexto) if contexto else None,
        )


async def listar_proceso_detalle(
    proceso_id: uuid.UUID, intento_id: int | None = None,
    page: int = 1, page_size: int = 50,
    clasificacion: str | None = None, min_score: float | None = None,
    ordenar_por: str = "mcp_score", direccion: str = "desc",
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        where = ["proceso_id = $1"]
        params = [proceso_id]
        idx = 2
        if intento_id is not None:
            where.append(f"intento_id = ${idx}")
            params.append(intento_id)
            idx += 1
        if clasificacion:
            where.append(f"clasificacion = ${idx}")
            params.append(clasificacion)
            idx += 1
        if min_score is not None:
            where.append(f"mcp_score >= ${idx}")
            params.append(min_score)
            idx += 1

        dir_sql = "ASC" if direccion.upper() == "ASC" else "DESC"
        order_col = "mcp_score" if ordenar_por in ("mcp_score", "nit", "created_at") else "mcp_score"
        offset = (page - 1) * page_size

        count_row = await conn.fetchval(
            f"SELECT COUNT(*) FROM proceso_detalle WHERE {' AND '.join(where)}",
            *params,
        )
        rows = await conn.fetch(
            f"SELECT * FROM proceso_detalle WHERE {' AND '.join(where)} ORDER BY {order_col} {dir_sql} LIMIT ${idx} OFFSET ${idx + 1}",
            *params, page_size, offset,
        )
        return count_row or 0, [dict(r) for r in rows]


async def listar_errores(
    proceso_id: uuid.UUID, intento_id: int | None = None,
    capa: str | None = None, nit: str | None = None,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        where_proc = ["proceso_id = $1"]
        params_proc = [proceso_id]
        idx = 2
        if intento_id is not None:
            where_proc.append(f"intento_id = ${idx}")
            params_proc.append(intento_id)
            idx += 1
        if capa:
            where_proc.append(f"capa = ${idx}")
            params_proc.append(capa)
            idx += 1

        where_det = ["1=1"]
        params_det = []
        idx_det = 1
        if nit:
            where_det.append(f"nit = ${idx_det}")
            params_det.append(nit)
            idx_det += 1
        if capa:
            where_det.append(f"capa = ${idx_det}")
            params_det.append(capa)
            idx_det += 1

        errores_proc = await conn.fetch(
            f"SELECT * FROM proceso_errores WHERE {' AND '.join(where_proc)} ORDER BY created_at DESC",
            *params_proc,
        )
        errores_det = await conn.fetch(
            f"SELECT * FROM proceso_detalle_errores WHERE {' AND '.join(where_det)} ORDER BY created_at DESC",
            *params_det,
        )
        return [dict(r) for r in errores_proc], [dict(r) for r in errores_det]


async def actualizar_estado_proceso(id: uuid.UUID, estado: str, **kwargs):
    pool = await get_pool()
    async with pool.acquire() as conn:
        sets = ["estado = $1"]
        params = [estado]
        idx = 2
        for key, val in kwargs.items():
            sets.append(f"{key} = ${idx}")
            params.append(val)
            idx += 1
        params.append(id)
        await conn.execute(f"UPDATE procesos SET {', '.join(sets)} WHERE id = ${idx - 1}", *params)


async def obtener_historial_intentos(proceso_id: uuid.UUID) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM proceso_intentos WHERE proceso_id = $1 ORDER BY numero_intento DESC",
            proceso_id,
        )
        return [dict(r) for r in rows]


async def obtener_cliente_por_id(cliente_id: uuid.UUID) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM clientes WHERE id = $1", cliente_id)
        return dict(row) if row else None

import logging

from infrastructure.mcp.oracle_adapter import MCPClient

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 100

PAGINAR_CONTRIBUYENTES_SQL = """
SELECT c.nit, c.razon_social, c.ciiu, c.regimen
FROM contribuyentes c
WHERE c.tipo_regimen = :tipo_regimen
  AND c.ciiu IN ({actividades_placeholders})
  AND c.vigencia >= TO_DATE(:vigencia_ini, 'YYYY-MM-DD')
  AND c.vigencia <= TO_DATE(:vigencia_fin, 'YYYY-MM-DD')
ORDER BY c.nit
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
"""

OBTENER_CONTRIBUYENTE_SQL = """
SELECT c.nit, c.razon_social, c.ciiu, c.regimen, r.rues_estado
FROM contribuyentes c
LEFT JOIN rues r ON c.nit = r.nit
WHERE c.nit = :nit
"""

OBTENER_DECLARACIONES_SQL = """
SELECT periodo, base_gravable, tarifa, impuesto
FROM declaraciones_ica
WHERE nit = :nit AND periodo = :periodo
ORDER BY periodo
"""

OBTENER_EXOGENA_SQL = """
SELECT periodo, ingresos
FROM exogena_dian
WHERE nit = :nit AND periodo = :periodo
ORDER BY periodo
"""


async def paginar_contribuyentes(
    client: MCPClient,
    vigencia_ini: str,
    vigencia_fin: str,
    tipo_regimen: str,
    actividades_economicas: list[str],
    periodo: str,
    page_size: int = DEFAULT_PAGE_SIZE,
):
    actividades_placeholders = ", ".join(f":a{i}" for i in range(len(actividades_economicas)))
    sql = PAGINAR_CONTRIBUYENTES_SQL.format(actividades_placeholders=actividades_placeholders)

    bind_params = {
        "tipo_regimen": tipo_regimen,
        "vigencia_ini": vigencia_ini,
        "vigencia_fin": vigencia_fin,
        **{f"a{i}": act for i, act in enumerate(actividades_economicas)},
    }

    offset = 0
    total_obtenidos = 0

    while True:
        logger.info("MCP: solicitando offset=%d limit=%d", offset, page_size)
        params = {**bind_params, "offset": offset, "limit": page_size}
        result = await client.call_tool("EXECUTE_SQL", {
            "query": sql,
            "bind_params": params,
        })

        if not result:
            break

        items = result if isinstance(result, list) else [result]
        if not items:
            break

        for item in items:
            yield item
            total_obtenidos += 1

        if len(items) < page_size:
            break

        offset += page_size

    logger.info("MCP: paginación completada — %d contribuyentes obtenidos", total_obtenidos)


async def obtener_datos_fiscales(client: MCPClient, nit: str, periodo: str) -> dict | None:
    logger.info("MCP: solicitando datos fiscales para NIT %s periodo %s", nit, periodo)

    contribuyente = await client.call_tool("EXECUTE_SQL", {
        "query": OBTENER_CONTRIBUYENTE_SQL,
        "bind_params": {"nit": nit},
    })

    if not contribuyente:
        return None

    row = contribuyente[0] if isinstance(contribuyente, list) else contribuyente

    declaraciones = await client.call_tool("EXECUTE_SQL", {
        "query": OBTENER_DECLARACIONES_SQL,
        "bind_params": {"nit": nit, "periodo": periodo},
    })
    exogena = await client.call_tool("EXECUTE_SQL", {
        "query": OBTENER_EXOGENA_SQL,
        "bind_params": {"nit": nit, "periodo": periodo},
    })

    return {
        "nit": row.get("nit", nit),
        "razon_social": row.get("razon_social", ""),
        "ciiu": row.get("ciiu", ""),
        "regimen": row.get("regimen", ""),
        "declaraciones_ica": declaraciones if isinstance(declaraciones, list) else [],
        "exogena_dian": exogena if isinstance(exogena, list) else [],
        "rues_estado": row.get("rues_estado", ""),
    }

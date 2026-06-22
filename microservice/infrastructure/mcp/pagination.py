import logging
from typing import AsyncGenerator

from infrastructure.mcp.oracle_adapter import MCPClient

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 100


async def paginar_contribuyentes(
    client: MCPClient,
    vigencia_ini: str,
    vigencia_fin: str,
    tipo_regimen: str,
    actividades_economicas: list[str],
    periodo: str,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> AsyncGenerator[dict, None]:
    page = 1
    total_obtenidos = 0

    while True:
        logger.info("MCP: solicitando página %d (page_size=%d)", page, page_size)
        result = await client.call_tool("buscar_contribuyentes", {
            "vigencia_ini": vigencia_ini,
            "vigencia_fin": vigencia_fin,
            "tipo_regimen": tipo_regimen,
            "actividades_economicas": actividades_economicas,
            "periodo": periodo,
            "page": page,
            "page_size": page_size,
        })

        if not result or isinstance(result, str):
            logger.warning("MCP: respuesta vacía o inválida en página %d", page)
            break

        items = result if isinstance(result, list) else [result]
        if not items:
            break

        for item in items:
            yield item
            total_obtenidos += 1

        if len(items) < page_size:
            break

        page += 1

    logger.info("MCP: paginación completada — %d contribuyentes obtenidos en %d páginas", total_obtenidos, page)


async def obtener_datos_fiscales(client: MCPClient, nit: str, periodo: str) -> dict | None:
    logger.info("MCP: solicitando datos fiscales para NIT %s", nit)
    result = await client.call_tool("obtener_datos_fiscales", {
        "nit": nit,
        "periodo": periodo,
    })
    return result if isinstance(result, dict) else None

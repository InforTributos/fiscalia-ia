import logging
from typing import AsyncGenerator

from fiscal_mcp.client import MCPClient as MCPTransport
from fiscal_mcp.pagination import paginar_contribuyentes, obtener_datos_fiscales

logger = logging.getLogger(__name__)


class AGT05MCPClient:
    def __init__(self, command: str = "python", args: list[str] | None = None):
        self.client = MCPTransport(command=command, args=args)

    async def buscar_contribuyentes(
        self,
        vigencia_ini: str,
        vigencia_fin: str,
        tipo_regimen: str,
        actividades_economicas: list[str],
        periodo: str,
    ) -> AsyncGenerator[dict, None]:
        async for item in paginar_contribuyentes(
            self.client,
            vigencia_ini=vigencia_ini,
            vigencia_fin=vigencia_fin,
            tipo_regimen=tipo_regimen,
            actividades_economicas=actividades_economicas,
            periodo=periodo,
        ):
            yield item

    async def obtener_datos(self, nit: str, periodo: str) -> dict | None:
        return await obtener_datos_fiscales(self.client, nit, periodo)

    async def close(self):
        await self.client.disconnect()

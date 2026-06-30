import logging
from collections.abc import AsyncGenerator

from infrastructure.mcp.oracle_adapter import OracleClient
from infrastructure.mcp.pagination import obtener_datos_fiscales, paginar_contribuyentes

logger = logging.getLogger(__name__)


class AGT05MCPClient:
    def __init__(self):
        self.client = OracleClient()

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
        pass

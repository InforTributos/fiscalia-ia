from domain.ports.contribuyente_repo import ContribuyenteRepo
from infrastructure.persistence import queries


class PostgresContribuyenteRepo(ContribuyenteRepo):
    async def obtener_por_nit(self, nit: str, periodo: str) -> dict | None:
        return await queries.obtener_cliente_por_nit(nit)

    async def listar_candidatos(
        self, vigencia_ini: str, vigencia_fin: str,
        tipo_regimen: str, actividades_economicas: list[str],
        periodo: str,
    ) -> list[dict]:
        return []

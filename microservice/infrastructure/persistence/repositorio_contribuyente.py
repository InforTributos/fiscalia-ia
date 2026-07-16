from domain.ports.contribuyente_repo import ContribuyenteRepo
from infrastructure.persistence import queries


class PostgresContribuyenteRepo(ContribuyenteRepo):
    async def obtener_por_nit(self, contribuyente_nit: str, periodo: str) -> dict | None:
        return await queries.obtener_entidad_por_nit(contribuyente_nit)

    async def listar_candidatos(
        self, vigencia_ini: str, vigencia_fin: str,
        tipo_regimen: str, actividades_economicas: list[str],
        periodo: str,
    ) -> list[dict]:
        return []

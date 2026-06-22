from abc import ABC, abstractmethod


class ContribuyenteRepo(ABC):
    @abstractmethod
    async def obtener_por_nit(self, nit: str, periodo: str) -> dict | None:
        ...

    @abstractmethod
    async def listar_candidatos(
        self, vigencia_ini: str, vigencia_fin: str,
        tipo_regimen: str, actividades_economicas: list[str],
        periodo: str,
    ):
        ...

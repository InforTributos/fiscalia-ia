from abc import ABC, abstractmethod

from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo


class ScoreRepo(ABC):
    @abstractmethod
    def obtener_srf(self, nit: NIT, periodo: Periodo) -> dict: ...


class AnalisisRepo(ABC):
    @abstractmethod
    def guardar_analisis(
        self,
        nit: NIT,
        periodo: Periodo,
        prompt: str,
        respuesta_ia: str,
        tokens_entrada: int = 0,
        tokens_salida: int = 0,
    ) -> int: ...

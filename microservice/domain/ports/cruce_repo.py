from abc import ABC, abstractmethod

from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo


class CruceRepo(ABC):
    @abstractmethod
    def obtener_cruces(self, nit: NIT, periodo: Periodo) -> list[dict]: ...

from abc import ABC, abstractmethod
from domain.value_objects.nit import NIT
from domain.entities.contribuyente import Contribuyente


class ContribuyenteRepo(ABC):
    @abstractmethod
    def obtener_por_nit(self, nit: NIT) -> Contribuyente:
        ...

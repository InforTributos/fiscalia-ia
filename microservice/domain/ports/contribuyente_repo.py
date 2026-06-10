from abc import ABC, abstractmethod

from domain.entities.contribuyente import Contribuyente
from domain.value_objects.nit import NIT


class ContribuyenteRepo(ABC):
    @abstractmethod
    def obtener_por_nit(self, nit: NIT) -> Contribuyente: ...

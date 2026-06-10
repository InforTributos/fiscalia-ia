from dataclasses import dataclass
from typing import Optional
from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo


@dataclass
class Contribuyente:
    nit: NIT
    razon_social: str
    ciiu: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    direccion: Optional[str] = None

    @classmethod
    def desde_fila(cls, fila: dict):
        return cls(
            nit=NIT(fila.get("nit", "")),
            razon_social=fila.get("razon_social", ""),
            ciiu=fila.get("ciiu"),
            municipio=fila.get("municipio"),
            estado=fila.get("estado"),
            direccion=fila.get("direccion"),
        )

from dataclasses import dataclass

from domain.value_objects.nit import NIT


@dataclass
class Contribuyente:
    nit: NIT
    razon_social: str
    ciiu: str | None = None
    municipio: str | None = None
    estado: str | None = None
    direccion: str | None = None

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

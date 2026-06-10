from dataclasses import dataclass

from domain.value_objects.dinero import Dinero


@dataclass
class Hallazgo:
    tipo: str
    severidad: str
    descripcion: str
    diferencia: Dinero | None = None
    declarado: Dinero | None = None
    referencia: Dinero | None = None
    ciiu: str | None = None
    explicacion_ia: str | None = None
    recomendacion: str | None = None

from dataclasses import dataclass
from typing import Optional
from domain.value_objects.dinero import Dinero
from domain.value_objects.score_riesgo import ScoreRiesgo


@dataclass
class Hallazgo:
    tipo: str
    severidad: str
    descripcion: str
    diferencia: Optional[Dinero] = None
    declarado: Optional[Dinero] = None
    referencia: Optional[Dinero] = None
    ciiu: Optional[str] = None
    explicacion_ia: Optional[str] = None
    recomendacion: Optional[str] = None

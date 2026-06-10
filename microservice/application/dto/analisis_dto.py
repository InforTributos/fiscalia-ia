from dataclasses import dataclass
from domain.entities.contribuyente import Contribuyente
from domain.entities.hallazgo import Hallazgo
from domain.entities.analisis import Analisis
from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo
from domain.value_objects.score_riesgo import ScoreRiesgo
from domain.value_objects.dinero import Dinero


@dataclass
class AnalisisDTO:
    nit: str
    periodo: str
    score_riesgo: float
    nivel_riesgo: str
    hallazgos: list[dict]
    explicacion_srf: str
    tiempo_analisis_ms: int
    cache_hit: bool = False
    modo_degradado: bool = False

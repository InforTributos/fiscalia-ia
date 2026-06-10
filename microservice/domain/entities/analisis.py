from dataclasses import dataclass
from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo
from domain.value_objects.score_riesgo import ScoreRiesgo
from domain.entities.hallazgo import Hallazgo


@dataclass
class Analisis:
    nit: NIT
    periodo: Periodo
    score: ScoreRiesgo
    hallazgos: list[Hallazgo]
    explicacion_srf: str
    modo_degradado: bool = False
    cache_hit: bool = False

from dataclasses import dataclass


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

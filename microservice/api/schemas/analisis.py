from pydantic import BaseModel
from typing import Optional


class HallazgoDTO(BaseModel):
    tipo: str
    severidad: str
    descripcion: str
    diferencia: Optional[float] = None
    ciiu: Optional[str] = None


class AnalisisResponse(BaseModel):
    nit: str
    periodo: str
    score_riesgo: float
    nivel_riesgo: str
    hallazgos: list[HallazgoDTO]
    explicacion_srf: str
    tiempo_analisis_ms: int
    cache_hit: bool = False
    modo_degradado: bool = False

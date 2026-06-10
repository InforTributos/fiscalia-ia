from pydantic import BaseModel


class ComponenteSRFDTO(BaseModel):
    nombre: str
    valor: float
    peso: float


class ScoreResponse(BaseModel):
    nit: str
    srf: float
    nivel: str
    componentes: list[ComponenteSRFDTO]
    explicacion_ia: str
    tiempo_analisis_ms: int

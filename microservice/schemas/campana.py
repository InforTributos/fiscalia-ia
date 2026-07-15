from uuid import UUID

from pydantic import BaseModel, Field


class CampanaRequest(BaseModel):
    periodo: str = Field(..., description="Año fiscal, ej. '2024'")
    actividad_economica: str | None = Field(None, description="Código CIIU opcional para filtrar candidatos")
    nombre: str = Field("Campaña fiscalización", description="Nombre descriptivo de la campaña")
    umbral_retenciones_pct: float = Field(5.0, ge=0, le=100, description="Umbral porcentual para inexactos retenciones")


class CampanaResponse(BaseModel):
    proceso_id: UUID
    intento_id: int
    estado: str
    nombre: str
    mensaje: str

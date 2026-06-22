from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProcesoRequest(BaseModel):
    cliente_nit: str = Field(..., description="NIT del cliente que solicita (auditor)")
    nombre: str = Field(..., description="Nombre descriptivo del proceso")
    vigencia_ini: str = Field(..., description="Fecha inicial del período (YYYY-MM-DD)")
    vigencia_fin: str = Field(..., description="Fecha final del período (YYYY-MM-DD)")
    tipo_regimen: str = Field(..., description="COMUN / SIMPLIFICADO")
    actividades_economicas: list[str] = Field(..., description="Lista de códigos CIIU")
    periodo: str = Field(..., description="Año fiscal")


class ProcesoResumen(BaseModel):
    total_nits: int = 0
    omisos: int = 0
    exactos: int = 0
    inexactos: int = 0


class ProcesoAnalisis(BaseModel):
    estado: str = "EN_COLA"
    mensaje: str = ""


class ProcesoResponse(BaseModel):
    proceso_id: UUID
    intento_id: int
    estado: str
    nombre: str
    cliente_nit: str
    resumen: ProcesoResumen
    proceso_analisis: ProcesoAnalisis
    created_at: datetime

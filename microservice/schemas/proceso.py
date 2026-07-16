from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ProcesoRequest(BaseModel):
    entidad_nit: str = Field(..., description="NIT de la entidad fiscalizadora (municipio)")
    nombre: str = Field(..., description="Nombre descriptivo del proceso")
    vigencia_ini: str = Field(..., description="Fecha inicial del período (YYYY-MM-DD)")
    vigencia_fin: str = Field(..., description="Fecha final del período (YYYY-MM-DD)")
    tipo_regimen: str = Field(..., description="COMUN / SIMPLIFICADO")
    actividades_economicas: list[str] = Field(..., description="Lista de códigos CIIU")
    periodo: str = Field(..., description="Año fiscal")

    tipo: Literal["BASICO", "COMPLETO"] = Field(
        "BASICO",
        description="BASICO=SRF+LLM (paralelo), COMPLETO=BASICO+comportamiento+reglas+score+resumen",
    )
    max_nits: int = Field(0, ge=0, description="Límite de NITs a procesar (0=ilimitado)")
    umbral_retenciones_pct: float = Field(
        5.0, ge=0, le=100, description="Umbral porcentual para inexactos retenciones"
    )


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
    entidad_nit: str
    resumen: ProcesoResumen
    proceso_analisis: ProcesoAnalisis
    created_at: datetime

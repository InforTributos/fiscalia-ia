from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenciaInput(BaseModel):
    fuente: str
    referencia_registro: str | None = None
    descripcion: str
    snapshot: dict = Field(default_factory=dict)


class CrearHallazgoRequest(BaseModel):
    nit: str
    regla: str
    periodo: str
    tipo_hallazgo: str | None = None
    fuerza_probatoria: str | None = None
    brecha_valor: float = 0
    impuesto_estimado: float = 0
    reincidencia: int = 0
    corroboracion: int = 1
    resumen: str | None = None
    metadata: dict = Field(default_factory=dict)
    evidencias: list[EvidenciaInput] = Field(default_factory=list)


class PerfilFiscalRequest(BaseModel):
    nit: str
    periodo: str
    reglas: list[str] | None = None
    declaraciones_ica: list[dict] = Field(default_factory=list)
    retenciones_ica: list[dict] = Field(default_factory=list)
    exogena_dian: list[dict] = Field(default_factory=list)
    facturacion_electronica: list[dict] = Field(default_factory=list)
    contratos_publicos: list[dict] = Field(default_factory=list)
    senales_actividad: list[dict] = Field(default_factory=list)
    indicadores_sectoriales: dict = Field(default_factory=dict)
    historico_bases: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    class Config:
        extra = "allow"


class EvidenciaResponse(BaseModel):
    id: UUID
    hallazgo_id: UUID
    fuente: str
    referencia_registro: str | None = None
    descripcion: str
    snapshot: dict = Field(default_factory=dict)
    created_at: datetime


class RevisionRequest(BaseModel):
    funcionario_id: str
    decision: str
    motivo: str | None = None


class RevisionResponse(BaseModel):
    id: UUID
    hallazgo_id: UUID
    funcionario_id: str
    decision: str
    motivo: str | None = None
    created_at: datetime


class RevisionAgenteRequest(BaseModel):
    usar_ia: bool = True


class RevisionAgenteResponse(BaseModel):
    id: UUID
    hallazgo_id: UUID
    agente: str
    version: str
    resultado: dict = Field(default_factory=dict)
    modo_degradado: bool
    tokens_entrada: int = 0
    tokens_salida: int = 0
    created_at: datetime


class HallazgoResponse(BaseModel):
    id: UUID
    nit: str
    regla: str
    periodo: str
    tipo_hallazgo: str
    fuerza_probatoria: str
    brecha_valor: float
    impuesto_estimado: float
    score: float
    score_componentes: dict = Field(default_factory=dict)
    ventana_limite: date
    accionable: bool
    estado: str
    resumen: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    evidencias: list[EvidenciaResponse] = Field(default_factory=list)
    revisiones: list[RevisionResponse] = Field(default_factory=list)


class ListaHallazgosResponse(BaseModel):
    total: int
    page: int
    page_size: int
    resultados: list[HallazgoResponse]


class EvaluacionReglasResponse(BaseModel):
    total: int
    resultados: list[CrearHallazgoRequest]

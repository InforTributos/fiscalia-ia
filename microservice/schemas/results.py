from uuid import UUID

from pydantic import BaseModel, Field


class Paginacion(BaseModel):
    page: int
    page_size: int
    total_registros: int
    total_paginas: int


class HallazgoResult(BaseModel):
    tipo: str
    severidad: str | None = None
    explicacion_ia: str | None = None
    detalle: dict = Field(default_factory=dict)


class ResultadoDetalle(BaseModel):
    contribuyente_nit: str
    razon_social: str | None = None
    ciiu: str | None = None
    clasificacion: str
    mcp_score: float | None = None
    mcp_razon: str | None = None
    srf_total: float | None = None
    nivel_riesgo: str | None = None
    hallazgos: list[HallazgoResult] = []
    explicacion_ia: str | None = None


class ResultsResponse(BaseModel):
    proceso_id: UUID
    estado: str
    intento_id: int | None = None
    parcial: bool = False
    paginacion: Paginacion
    resultados: list[ResultadoDetalle] = []


class ResultsQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    intento_id: int | None = None
    include_partial: bool = False
    clasificacion: str | None = None
    min_score: float | None = None
    ordenar_por: str = "mcp_score"
    direccion: str = "desc"

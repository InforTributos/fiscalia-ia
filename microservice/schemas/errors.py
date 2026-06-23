from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ErrorProceso(BaseModel):
    id: int
    intento_id: int
    capa: str
    codigo: str
    mensaje: str
    contexto: dict | None = None
    created_at: datetime | None = None


class ErrorDetalle(BaseModel):
    nit: str
    capa: str
    codigo: str
    mensaje: str
    contexto: dict | None = None
    created_at: datetime | None = None


class ErrorsResponse(BaseModel):
    proceso_id: UUID
    errores_proceso: list[ErrorProceso] = []
    errores_detalle: list[ErrorDetalle] = []
    total_errores_proceso: int = 0
    total_errores_detalle: int = 0


class ErrorsQueryParams(BaseModel):
    intento_id: int | None = None
    capa: str | None = None
    nit: str | None = None

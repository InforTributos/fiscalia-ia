from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IntentoHistorial(BaseModel):
    numero: int
    estado: str
    errores_count: int = 0
    started_at: datetime | None = None


class IntentoActual(BaseModel):
    numero: int
    estado: str
    procesados: int = 0
    errores: int = 0


class Progreso(BaseModel):
    porcentaje: float = 0.0
    total_nits: int = 0
    procesados: int = 0
    faltantes: int = 0


class ClasificacionProgreso(BaseModel):
    total: int = 0
    procesados: int = 0


class StatusResponse(BaseModel):
    proceso_id: UUID
    estado: str
    cliente_nit: str
    intento_actual: IntentoActual | None = None
    intentos_historial: list[IntentoHistorial] = []
    progreso: Progreso | None = None
    clasificacion: dict[str, ClasificacionProgreso] | None = None
    started_at: datetime | None = None
    ultimo_update: datetime | None = None

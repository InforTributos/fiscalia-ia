import logging
import uuid

from domain.errors import EntidadNoEncontradoError, FiscalIAError
from fastapi import APIRouter, Query
from infrastructure.persistence.repositorio_proceso import PostgresProcesoRepo
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()
repo = PostgresProcesoRepo()


class EntidadRequest(BaseModel):
    entidad_nit: str = Field(..., description="NIT de la entidad fiscalizadora")
    nombre: str = Field(..., description="Nombre oficial de la entidad (ej: Municipio de Valledupar)")
    email: str | None = Field(None, description="Correo de contacto (opcional)")


class EntidadResponse(BaseModel):
    id: uuid.UUID
    entidad_nit: str
    nombre: str
    email: str | None = None
    activo: bool = True


@router.post("/entidad_fiscalizadora", status_code=201, response_model=EntidadResponse)
async def crear_entidad(req: EntidadRequest):
    existing = await repo.obtener_entidad_por_nit(req.entidad_nit)
    if existing:
        raise FiscalIAError(f"Ya existe una entidad con el NIT {req.entidad_nit}")
    entidad_id = await repo.crear_entidad(req.entidad_nit, req.nombre, req.email)
    if not entidad_id:
        raise FiscalIAError("No se pudo crear la entidad fiscalizadora")
    return EntidadResponse(
        id=entidad_id,
        entidad_nit=req.entidad_nit,
        nombre=req.nombre,
        email=req.email,
    )


@router.get("/entidad_fiscalizadora/{entidad_nit}", response_model=EntidadResponse)
async def obtener_entidad(entidad_nit: str):
    entidad = await repo.obtener_entidad_por_nit(entidad_nit)
    if not entidad:
        raise EntidadNoEncontradoError(entidad_nit)
    return EntidadResponse(
        id=entidad["id"],
        entidad_nit=entidad["nit"],
        nombre=entidad["razon_social"],
        email=entidad.get("email"),
        activo=entidad.get("activo", True),
    )


@router.get("/entidades_fiscalizadoras")
async def listar_entidades(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return {"page": page, "page_size": page_size, "mensaje": "Listado no implementado"}

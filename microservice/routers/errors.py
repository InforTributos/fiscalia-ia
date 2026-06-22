import uuid

from domain.errors import ProcesoNoEncontradoError
from fastapi import APIRouter, Query
from infrastructure.persistence import queries
from schemas.errors import ErrorsResponse, ErrorProceso, ErrorDetalle

router = APIRouter()


@router.get("/proceso/{proceso_id}/errors", response_model=ErrorsResponse)
async def consultar_errores(
    proceso_id: uuid.UUID,
    intento_id: int | None = None,
    capa: str | None = None,
    nit: str | None = None,
):
    proceso = await queries.obtener_proceso(proceso_id)
    if not proceso:
        raise ProcesoNoEncontradoError(str(proceso_id))

    errores_proc, errores_det = await queries.listar_errores(
        proceso_id=proceso_id,
        intento_id=intento_id,
        capa=capa,
        nit=nit,
    )

    return ErrorsResponse(
        proceso_id=proceso_id,
        errores_proceso=[ErrorProceso(**e) for e in errores_proc],
        errores_detalle=[ErrorDetalle(**e) for e in errores_det],
        total_errores_proceso=len(errores_proc),
        total_errores_detalle=len(errores_det),
    )

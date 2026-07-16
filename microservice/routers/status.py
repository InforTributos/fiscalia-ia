import uuid

from domain.errors import ProcesoNoEncontradoError
from fastapi import APIRouter
from infrastructure.persistence.repositorio_proceso import PostgresProcesoRepo
from schemas.status import ClasificacionProgreso, IntentoActual, IntentoHistorial, Progreso, StatusResponse

router = APIRouter()
repo = PostgresProcesoRepo()


@router.get("/proceso/{proceso_id}/status", response_model=StatusResponse)
async def consultar_status(proceso_id: uuid.UUID):
    proceso = await repo.obtener_proceso(proceso_id)
    if not proceso:
        raise ProcesoNoEncontradoError(str(proceso_id))

    intento_actual = await repo.obtener_ultimo_intento(proceso_id)
    historial_rows = await repo.obtener_historial_intentos(proceso_id)

    entidad = await repo.obtener_entidad_por_id(proceso["entidad_id"]) if proceso.get("entidad_id") else None

    intento_actual_dto = None
    if intento_actual:
        intento_actual_dto = IntentoActual(
            numero=intento_actual["numero_intento"],
            estado=intento_actual["estado"],
            procesados=intento_actual["procesados"] or 0,
            errores=intento_actual["errores_count"] or 0,
        )

    historial = []
    if historial_rows:
        for h in historial_rows:
            historial.append(IntentoHistorial(
                numero=h["numero_intento"],
                estado=h["estado"],
                errores_count=h.get("errores_count", 0),
                started_at=h.get("started_at"),
            ))

    candidatos = proceso.get("candidatos", 0) or 0
    procesados = (intento_actual["procesados"] or 0) if intento_actual else 0
    faltantes = candidatos - procesados if candidatos > procesados else 0
    porcentaje = round((procesados / candidatos * 100), 1) if candidatos > 0 else 0.0

    return StatusResponse(
        proceso_id=proceso_id,
        estado=proceso["estado"],
        entidad_nit=entidad["nit"] if entidad else "",
        intento_actual=intento_actual_dto,
        intentos_historial=historial,
        progreso=Progreso(
            porcentaje=porcentaje,
            total_nits=candidatos,
            procesados=procesados,
            faltantes=faltantes,
        ),
        clasificacion={
            "omisos": ClasificacionProgreso(total=proceso.get("omisos", 0) or 0, procesados=0),
            "inexactos": ClasificacionProgreso(total=proceso.get("inexactos", 0) or 0, procesados=0),
        },
        started_at=intento_actual.get("started_at") if intento_actual else None,
        ultimo_update=intento_actual.get("completed_at") if intento_actual else None,
    )

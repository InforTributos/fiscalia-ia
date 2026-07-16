import asyncio
import logging
import uuid

from domain.errors import EntidadNoEncontradoError, FiscalIAError, ProcesoEnProcesoError
from fastapi import APIRouter
from infrastructure.persistence.repositorio_proceso import PostgresProcesoRepo
from schemas.proceso import ProcesoAnalisis, ProcesoRequest, ProcesoResponse, ProcesoResumen
from tasks.analisis_task import analizar_proceso

logger = logging.getLogger(__name__)

router = APIRouter()
repo = PostgresProcesoRepo()


async def _lanzar_analisis(proceso_id: uuid.UUID, intento_id: int, criteria: dict):
    from tasks.concurrency import esperar_turno, liberar_slot

    cancel_event = await esperar_turno(str(proceso_id))
    try:
        if cancel_event.is_set():
            logger.warning("Proceso %s cancelado mientras esperaba turno", proceso_id)
            await repo.actualizar_estado_proceso(proceso_id, "INTERRUMPIDO")
            return
        await analizar_proceso(str(proceso_id), intento_id, criteria)
    except asyncio.CancelledError:
        await repo.actualizar_estado_proceso(proceso_id, "INTERRUMPIDO")
    except Exception as e:
        logger.error("Error fatal en proceso %s: %s", proceso_id, e)
        await repo.actualizar_estado_proceso(proceso_id, "ERROR")
    finally:
        liberar_slot(str(proceso_id))


@router.post("/proceso", status_code=201, response_model=ProcesoResponse)
async def crear_proceso(req: ProcesoRequest):
    entidad = await repo.obtener_entidad_por_nit(req.entidad_nit)
    if not entidad:
        raise EntidadNoEncontradoError(req.entidad_nit)
    entidad_id = entidad["id"]

    criteria = {
        "vigencia_ini": req.vigencia_ini,
        "vigencia_fin": req.vigencia_fin,
        "tipo_regimen": req.tipo_regimen,
        "actividades_economicas": req.actividades_economicas,
        "periodo": req.periodo,
        "tipo": req.tipo,
        "max_nits": req.max_nits,
        "umbral_retenciones_pct": req.umbral_retenciones_pct,
    }

    existing = await repo.obtener_proceso_por_criteria(entidad_id, criteria)
    if existing and existing["estado"] in ("EN_PROCESO", "EN_COLA", "PREFILTRANDO", "PENDIENTE"):
        raise ProcesoEnProcesoError(
            str(existing["id"]),
            mensaje=f"Ya existe un proceso activo con los mismos criterios: {str(existing['id'])}",
        )

    numero_intento = 1
    if existing and existing["estado"] in ("COMPLETADO", "ERROR", "INTERRUMPIDO"):
        numero_intento = (existing.get("intentos_total") or 0) + 1

    proceso_id = await repo.crear_proceso(entidad_id, req.nombre, criteria)
    if not proceso_id:
        raise FiscalIAError("No se pudo crear el proceso")

    intento_id = await repo.crear_intento(proceso_id, numero_intento)
    if not intento_id:
        raise FiscalIAError("No se pudo crear el intento")

    await repo.actualizar_estado_proceso(proceso_id, "EN_COLA")
    await repo.actualizar_estado_intento(intento_id, "EN_COLA")

    asyncio.create_task(_lanzar_analisis(proceso_id, intento_id, criteria))

    return ProcesoResponse(
        proceso_id=proceso_id,
        intento_id=intento_id,
        estado="EN_COLA",
        nombre=req.nombre,
        entidad_nit=req.entidad_nit,
        resumen=ProcesoResumen(),
        proceso_analisis=ProcesoAnalisis(
            estado="EN_COLA",
            mensaje="Proceso creado. Iniciando pre-filtrado de candidatos en Oracle.",
        ),
        created_at=__import__("datetime").datetime.now(),
    )


@router.post("/proceso/{proceso_id}/cancelar")
async def cancelar_proceso(proceso_id: str):
    pid = uuid.UUID(proceso_id)
    proceso = await repo.obtener_proceso(pid)
    if not proceso:
        raise FiscalIAError("Proceso no encontrado")
    if proceso["estado"] not in ("EN_PROCESO", "EN_COLA", "PREFILTRANDO", "PENDIENTE"):
        raise FiscalIAError(
            f"El proceso esta en estado {proceso['estado']}, no se puede cancelar"
        )
    await repo.actualizar_estado_proceso(pid, "INTERRUMPIDO")

    from tasks.concurrency import cancelar as cancelar_activo
    cancelar_activo(proceso_id)

    return {"proceso_id": proceso_id, "estado": "INTERRUMPIDO"}

import asyncio
import logging
import uuid

from domain.errors import FiscalIAError
from fastapi import APIRouter
from infrastructure.persistence.repositorio_proceso import PostgresProcesoRepo
from schemas.campana import CampanaRequest, CampanaResponse
from tasks.campana_task import ejecutar_campana

logger = logging.getLogger(__name__)

router = APIRouter()
repo = PostgresProcesoRepo()


async def _lanzar_campana(
    proceso_id: uuid.UUID, intento_id: int,
    periodo: str, actividad_economica: str | None, umbral_pct: float,
):
    from tasks.concurrency import esperar_turno, liberar_slot

    cancel_event = await esperar_turno(str(proceso_id))
    try:
        if cancel_event.is_set():
            logger.warning("Campana %s cancelada mientras esperaba turno", proceso_id)
            await repo.actualizar_estado_proceso(proceso_id, "INTERRUMPIDO")
            return
        await ejecutar_campana(
            str(proceso_id), intento_id, periodo, actividad_economica, umbral_pct,
        )
    except asyncio.CancelledError:
        await repo.actualizar_estado_proceso(proceso_id, "INTERRUMPIDO")
    except Exception as e:
        logger.error("Error fatal en campana %s: %s", proceso_id, e)
        await repo.actualizar_estado_proceso(proceso_id, "ERROR")
    finally:
        liberar_slot(str(proceso_id))


@router.post("/campana", status_code=201, response_model=CampanaResponse)
async def crear_campana(req: CampanaRequest):
    criteria = {
        "tipo": "CAMPANA",
        "periodo": req.periodo,
        "actividad_economica": req.actividad_economica,
        "umbral_retenciones_pct": req.umbral_retenciones_pct,
    }

    proceso_id = await repo.crear_proceso(None, req.nombre, criteria)
    if not proceso_id:
        raise FiscalIAError("No se pudo crear el proceso de campana")

    numero_intento = 1

    intento_id = await repo.crear_intento(proceso_id, numero_intento)
    if not intento_id:
        raise FiscalIAError("No se pudo crear el intento")

    await repo.actualizar_estado_proceso(proceso_id, "EN_COLA")
    await repo.actualizar_estado_intento(intento_id, "EN_COLA")

    asyncio.create_task(_lanzar_campana(
        proceso_id, intento_id, req.periodo, req.actividad_economica, req.umbral_retenciones_pct,
    ))

    return CampanaResponse(
        proceso_id=proceso_id,
        intento_id=intento_id,
        estado="EN_COLA",
        nombre=req.nombre,
        mensaje="Campana encolada. Se iniciara el descubrimiento de candidatos y analisis IA.",
    )

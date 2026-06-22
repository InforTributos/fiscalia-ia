import asyncio
import logging
import uuid

from domain.errors import ProcesoEnProcesoError, FiscalIAError
from fastapi import APIRouter
from infrastructure.persistence.repositorio_proceso import PostgresProcesoRepo
from schemas.proceso import ProcesoRequest, ProcesoResponse, ProcesoResumen, ProcesoAnalisis
from tasks.analisis_task import analizar_proceso

logger = logging.getLogger(__name__)

router = APIRouter()
repo = PostgresProcesoRepo()


@router.post("/proceso", status_code=201, response_model=ProcesoResponse)
async def crear_proceso(req: ProcesoRequest):
    cliente = await repo.obtener_cliente_por_nit(req.cliente_nit)
    if not cliente:
        cliente_id = await repo.crear_cliente(req.cliente_nit, req.cliente_nit)
        if not cliente_id:
            raise FiscalIAError("No se pudo crear el cliente")
    else:
        cliente_id = cliente["id"]

    criteria = {
        "vigencia_ini": req.vigencia_ini,
        "vigencia_fin": req.vigencia_fin,
        "tipo_regimen": req.tipo_regimen,
        "actividades_economicas": req.actividades_economicas,
        "periodo": req.periodo,
    }

    existing = await repo.obtener_proceso_por_criteria(cliente_id, criteria)
    if existing and existing["estado"] in ("EN_PROCESO", "EN_COLA", "PREFILTRANDO", "PENDIENTE"):
        raise ProcesoEnProcesoError(
            str(existing["id"]),
            mensaje=f"Ya existe un proceso activo con los mismos criterios: {str(existing['id'])}",
        )

    numero_intento = 1
    if existing and existing["estado"] in ("COMPLETADO", "ERROR", "INTERRUMPIDO"):
        numero_intento = (existing.get("intentos_total") or 0) + 1

    proceso_id = await repo.crear_proceso(cliente_id, req.nombre, criteria)
    if not proceso_id:
        raise FiscalIAError("No se pudo crear el proceso")

    intento_id = await repo.crear_intento(proceso_id, numero_intento)
    if not intento_id:
        raise FiscalIAError("No se pudo crear el intento")

    await repo.actualizar_estado_proceso(proceso_id, "EN_COLA")
    await repo.actualizar_estado_intento(intento_id, "EN_COLA")

    asyncio.create_task(analizar_proceso(str(proceso_id), intento_id))

    return ProcesoResponse(
        proceso_id=proceso_id,
        intento_id=intento_id,
        estado="EN_COLA",
        nombre=req.nombre,
        cliente_nit=req.cliente_nit,
        resumen=ProcesoResumen(),
        proceso_analisis=ProcesoAnalisis(
            estado="EN_COLA",
            mensaje="Proceso encolado. Pendiente de conexión MCP para pre-filtrado y análisis IA.",
        ),
        created_at=__import__("datetime").datetime.now(),
    )

import logging
import uuid

from application.use_cases.orquestar_proceso import ProcesoOrchestrator
from infrastructure.llm.llm_service import LLMService
from infrastructure.persistence.repositorio_proceso import PostgresProcesoRepo
from tasks.retry import with_retry

logger = logging.getLogger(__name__)


async def analizar_proceso(proceso_id: str, intento_id: int):
    repo = PostgresProcesoRepo()
    orchestrator = ProcesoOrchestrator(LLMService(), repo)
    logger.info("Task: iniciando análisis de proceso %s (intento %d)", proceso_id, intento_id)

    total, rows = await repo.listar_proceso_detalle(
        proceso_id=uuid.UUID(proceso_id),
        intento_id=intento_id,
        page=1,
        page_size=10000,
    )

    await repo.actualizar_estado_proceso(uuid.UUID(proceso_id), "EN_PROCESO")
    await repo.actualizar_estado_intento(intento_id, "EN_PROCESO")

    procesados = 0
    errores = 0

    for row in rows:
        if row.get("clasificacion") in ("OMISO", "INEXACTO"):
            try:
                await with_retry(
                    orchestrator.ejecutar,
                    proceso_id, intento_id, row["nit"], row["id"],
                )
                procesados += 1
            except Exception as e:
                logger.error("Error procesando NIT %s: %s", row["nit"], str(e))
                errores += 1
                await repo.insertar_error_detalle(
                    row["id"], row["nit"], "PROCESO", "ANALISIS_FAIL", str(e),
                )

        await repo.actualizar_progreso_intento(intento_id, procesados, errores)

    estado_final = "COMPLETADO" if errores == 0 else "ERROR"
    await repo.actualizar_estado_intento(intento_id, estado_final)
    await repo.actualizar_estado_proceso(uuid.UUID(proceso_id), estado_final)

    logger.info("Task: proceso %s completado — %d OK, %d errores", proceso_id, procesados, errores)

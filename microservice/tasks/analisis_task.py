import asyncio
import logging
import uuid

from application.use_cases.orquestar_proceso import ProcesoOrchestrator
from config import settings
from infrastructure.llm.llm_service import LLMService
from infrastructure.mcp.oracle_adapter import OracleClient
from infrastructure.mcp.pagination import (
    obtener_inexactos_ciiu,
    obtener_inexactos_retenciones,
    obtener_omisos_conocidos,
    obtener_omisos_desconocidos,
)
from infrastructure.persistence.repositorio_proceso import PostgresProcesoRepo

logger = logging.getLogger(__name__)

BATCH = settings.batch_db_size or 50
CONCURRENCY = settings.nit_concurrency or 5


async def pre_filtrar(repo: PostgresProcesoRepo, proceso_id: str, intento_id: int, criteria: dict) -> dict:
    max_nits = criteria.get("max_nits", 0)
    logger.info("Pre-filtro: buscando candidatos para proceso %s (intento %d, max_nits=%d)", proceso_id, intento_id, max_nits)

    client = OracleClient()
    await client.initialize()
    periodo = criteria.get("periodo", "2024")

    await repo.actualizar_estado_proceso(uuid.UUID(proceso_id), "PREFILTRANDO")
    await repo.actualizar_estado_intento(intento_id, "PREFILTRANDO")

    total = 0
    conteos = {"OMISO": 0, "EXACTO": 0, "INEXACTO": 0}
    errores = 0
    buffer = []

    candidato_generators = [
        ("OMISO_CONOCIDO", lambda: obtener_omisos_conocidos(client, periodo, periodo)),
        ("OMISO_DESCONOCIDO", lambda: obtener_omisos_desconocidos(client, periodo)),
        ("INEXACTO_CIIU", lambda: obtener_inexactos_ciiu(client, periodo)),
        ("INEXACTO_RETENCIONES", lambda: obtener_inexactos_retenciones(client, periodo)),
    ]

    for tipo, gen_fn in candidato_generators:
        if max_nits and total >= max_nits:
            break
        clasificacion = "OMISO" if tipo.startswith("OMISO") else "INEXACTO"
        try:
            generator = gen_fn()
            async for item in generator:
                if max_nits and total >= max_nits:
                    break
                if tipo == "OMISO_DESCONOCIDO":
                    nit = item.get("nit", "")
                    razon_social = item.get("razon_social", "")
                    ciiu = str(item.get("ciiu", "") or "")
                else:
                    nit = item.get("idntfccion", "")
                    razon_social = item.get("nmbre_rzon_scial", "")
                    ciiu = str(item.get("id_actvdad_ecnmca", "") or "")

                if not nit:
                    continue

                buffer.append(dict(
                    proceso_id=uuid.UUID(proceso_id),
                    intento_id=intento_id,
                    nit=nit,
                    razon_social=razon_social,
                    ciiu=ciiu,
                    clasificacion=clasificacion,
                    mcp_razon=tipo,
                    detalle_clasificacion=f"{tipo} — detectado por consulta de pre-filtro MCP",
                ))
                total += 1
                conteos[clasificacion] += 1

                if len(buffer) >= BATCH:
                    await repo.bulk_insertar_detalle(buffer)
                    buffer.clear()
        except Exception as e:
            logger.error("Error en pre-filtro %s: %s", tipo, str(e))
            errores += 1
            await repo.insertar_error_proceso(
                uuid.UUID(proceso_id), intento_id, "MCP", f"MCP_{tipo}_FAIL", str(e),
            )

    if buffer:
        await repo.bulk_insertar_detalle(buffer)

    await repo.actualizar_estado_proceso(uuid.UUID(proceso_id), "PREFILTRADO_COMPLETADO")
    await repo.actualizar_estado_intento(intento_id, "PREFILTRADO_COMPLETADO")

    logger.info(
        "Pre-filtro: %d candidatos encontrados (OMISO=%d, INEXACTO=%d, errores=%d)",
        total, conteos["OMISO"], conteos["INEXACTO"], errores,
    )

    return {"total": total, **conteos, "errores": errores}


async def analizar_proceso(proceso_id: str, intento_id: int, criteria: dict):
    repo = PostgresProcesoRepo()
    logger.info("Task: iniciando análisis de proceso %s (intento %d)", proceso_id, intento_id)

    # Fase 1: Pre-filtro — buscar candidatos en Oracle (batch inserts)
    resumen = await pre_filtrar(repo, proceso_id, intento_id, criteria)

    if resumen["errores"] == 4:
        logger.error("Pre-filtro: fallaron todas las consultas de candidatos")
        await repo.actualizar_estado_proceso(uuid.UUID(proceso_id), "ERROR")
        await repo.actualizar_estado_intento(intento_id, "ERROR")
        await repo.insertar_error_proceso(
            uuid.UUID(proceso_id), intento_id, "MCP", "MCP_ALL_FAIL",
            "Fallaron todas las consultas de candidatos en el pre-filtro",
        )
        return

    if resumen["total"] == 0:
        logger.info("Pre-filtro: no se encontraron candidatos en los criterios")
        await repo.actualizar_estado_proceso(uuid.UUID(proceso_id), "COMPLETADO")
        await repo.actualizar_estado_intento(intento_id, "COMPLETADO")
        return

    # Fase 2: Análisis IA — procesar candidatos en paralelo con buffer batch
    await repo.actualizar_estado_proceso(uuid.UUID(proceso_id), "EN_PROCESO")
    await repo.actualizar_estado_intento(intento_id, "EN_PROCESO")

    orchestrator = ProcesoOrchestrator(LLMService(), repo)

    total, rows = await repo.listar_proceso_detalle(
        proceso_id=uuid.UUID(proceso_id),
        intento_id=intento_id,
        page=1,
        page_size=10000,
    )

    periodo = criteria.get("periodo", "2024")
    procesados = 0
    errores = 0
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    stop_event = asyncio.Event()

    from tasks.concurrency import esta_activo as _check_cancel

    async def _procesar(row: dict):
        nonlocal procesados, errores
        if stop_event.is_set():
            return
        async with sem:
            if stop_event.is_set() or not _check_cancel(proceso_id):
                stop_event.set()
                return
            if row.get("clasificacion") not in ("OMISO", "INEXACTO"):
                return
            try:
                await orchestrator.ejecutar(
                    proceso_id, intento_id, row["nit"], row["id"], periodo,
                )
                async with lock:
                    procesados += 1
            except Exception as e:
                logger.error("Error procesando NIT %s: %s", row["nit"], str(e))
                async with lock:
                    errores += 1
                await repo.insertar_error_detalle(
                    uuid.UUID(proceso_id), row["id"], row["nit"], "PROCESO", "ANALISIS_FAIL", str(e),
                )

    tasks = [_procesar(r) for r in rows]
    await asyncio.gather(*tasks)

    if stop_event.is_set():
        await repo.actualizar_estado_proceso(uuid.UUID(proceso_id), "INTERRUMPIDO")
        await repo.actualizar_estado_intento(intento_id, "INTERRUMPIDO", error_resumen="Cancelado externamente")
        return

    estado_final = "COMPLETADO" if errores == 0 else "ERROR"
    await repo.actualizar_estado_intento(intento_id, estado_final)
    await repo.actualizar_estado_proceso(uuid.UUID(proceso_id), estado_final)
    await repo.actualizar_progreso_intento(intento_id, procesados, errores)

    logger.info("Task: proceso %s completado — %d OK, %d errores", proceso_id, procesados, errores)

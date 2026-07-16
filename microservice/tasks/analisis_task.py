import asyncio
import json
import logging
import re
import time
import uuid

from application.use_cases.construir_perfil_fiscal import construir_perfil_fiscal_desde_datos_originales
from application.use_cases.gestionar_hallazgos import GestionarHallazgosUseCase
from application.use_cases.orquestar_proceso import ProcesoOrchestrator
from config import settings
from domain.behavioral.behavioral_score import calcular_score_comportamental
from domain.behavioral.peer_group import build_benchmark, build_contributor_metrics
from domain.behavioral.seasonal import analizar_patrones_temporales
from domain.fiscal.unified_score import calcular_score_fiscal_unificado
from domain.fiscalizacion.rule_engine import evaluar_reglas
from infrastructure.llm.llm_service import LLMService
from infrastructure.llm.prompts import construir_prompt
from infrastructure.mcp.behavioral import OracleBehavioralRepository
from infrastructure.mcp.oracle_adapter import OracleClient
from infrastructure.mcp.pagination import (
    calcular_page_size_dinamico,
    contar_inexactos_ciiu,
    contar_inexactos_retenciones,
    contar_omisos_conocidos,
    contar_omisos_desconocidos,
    obtener_datos_fiscales,
    obtener_inexactos_ciiu,
    obtener_inexactos_retenciones,
    obtener_omisos_conocidos,
    obtener_omisos_desconocidos,
)
from infrastructure.persistence import queries
from infrastructure.persistence.repositorio_proceso import PostgresProcesoRepo

logger = logging.getLogger(__name__)

CONCURRENCY = settings.nit_concurrency or 5


def _calcular_batch_size(total_estimado: int) -> int:
    if not settings.batch_auto_scale:
        return settings.batch_db_size or 50
    if total_estimado <= 0:
        return settings.batch_db_size or 50
    if total_estimado <= settings.batch_min_size:
        return max(1, total_estimado)
    if total_estimado <= 50:
        return total_estimado
    if total_estimado <= 500:
        return 50
    return min(settings.batch_max_size, total_estimado // 5)


async def pre_filtrar(repo: PostgresProcesoRepo, proceso_id: str, intento_id: int, criteria: dict) -> dict:
    max_nits = criteria.get("max_nits", 0)
    logger.info("Pre-filtro: buscando candidatos para proceso %s (intento %d, max_nits=%d)", proceso_id, intento_id, max_nits)

    client = OracleClient()
    await client.initialize()
    periodo = criteria.get("periodo", "2024")
    umbral_pct = criteria.get("umbral_retenciones_pct", 5.0)

    await repo.actualizar_estado_proceso(uuid.UUID(proceso_id), "PREFILTRANDO")
    await repo.actualizar_estado_intento(intento_id, "PREFILTRANDO")

    total = 0
    conteos = {"OMISO": 0, "EXACTO": 0, "INEXACTO": 0}
    errores = 0
    buffer = []

    # Fase 1: COUNT estimado por cada generador
    count_fns = [
        ("OMISO_CONOCIDO", lambda: contar_omisos_conocidos(client, periodo, periodo)),
        ("OMISO_DESCONOCIDO", lambda: contar_omisos_desconocidos(client, periodo)),
        ("INEXACTO_CIIU", lambda: contar_inexactos_ciiu(client, periodo)),
        ("INEXACTO_RETENCIONES", lambda: contar_inexactos_retenciones(client, periodo, umbral_pct=umbral_pct)),
    ]
    total_estimado = 0
    conteos_generador = []
    for tipo, count_fn in count_fns:
        try:
            count = await count_fn()
            total_estimado += count
            conteos_generador.append((tipo, count))
        except Exception as e:
            logger.warning("COUNT falló para %s: %s — se usará default", tipo, str(e))
            conteos_generador.append((tipo, 0))

    # Fase 2: calcular batch_size dinámico
    batch_size = _calcular_batch_size(total_estimado)
    page_size = calcular_page_size_dinamico(total_estimado)

    conteos_str = ", ".join(f"{t}={c}" for t, c in conteos_generador)
    logger.info(
        "Pre-filtro: total_estimado=%d, batch_size=%d, page_size=%d [%s]",
        total_estimado, batch_size, page_size, conteos_str,
    )

    # Fase 3: fetch con page_size dinámico
    gen_fns = [
        ("OMISO_CONOCIDO", lambda: obtener_omisos_conocidos(client, periodo, periodo, page_size=page_size)),
        ("OMISO_DESCONOCIDO", lambda: obtener_omisos_desconocidos(client, periodo, page_size=page_size)),
        ("INEXACTO_CIIU", lambda: obtener_inexactos_ciiu(client, periodo, page_size=page_size)),
        ("INEXACTO_RETENCIONES", lambda: obtener_inexactos_retenciones(client, periodo, page_size=page_size, umbral_pct=umbral_pct)),
    ]

    for tipo, gen_fn in gen_fns:
        if max_nits and total >= max_nits:
            break
        clasificacion = "OMISO" if tipo.startswith("OMISO") else "INEXACTO"
        try:
            generator = gen_fn()
            async for item in generator:
                if max_nits and total >= max_nits:
                    break
                if tipo == "OMISO_DESCONOCIDO":
                    contribuyente_nit = item.get("nit", "")
                    razon_social = item.get("razon_social", "")
                    ciiu = str(item.get("ciiu", "") or "")
                else:
                    contribuyente_nit = item.get("idntfccion", "")
                    razon_social = item.get("nmbre_rzon_scial", "")
                    ciiu = str(item.get("id_actvdad_ecnmca", "") or "")

                if not contribuyente_nit:
                    continue

                buffer.append(dict(
                    proceso_id=uuid.UUID(proceso_id),
                    intento_id=intento_id,
                    contribuyente_nit=contribuyente_nit,
                    razon_social=razon_social,
                    ciiu=ciiu,
                    clasificacion=clasificacion,
                    mcp_razon=tipo,
                    detalle_clasificacion=f"{tipo} — detectado por consulta de pre-filtro MCP",
                ))
                total += 1
                conteos[clasificacion] += 1

                if len(buffer) >= batch_size:
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

    await repo.actualizar_estado_proceso(
        uuid.UUID(proceso_id), "PREFILTRADO_COMPLETADO",
        total_nits=total,
        candidatos=total,
        omisos=conteos["OMISO"],
        inexactos=conteos["INEXACTO"],
        exactos=conteos.get("EXACTO", 0),
    )
    await repo.actualizar_estado_intento(intento_id, "PREFILTRADO_COMPLETADO")

    logger.info(
        "Pre-filtro: %d candidatos encontrados (OMISO=%d, INEXACTO=%d, errores=%d)",
        total, conteos["OMISO"], conteos["INEXACTO"], errores,
    )

    return {"total": total, **conteos, "errores": errores}


async def analizar_proceso(proceso_id: str, intento_id: int, criteria: dict):
    repo = PostgresProcesoRepo()
    logger.info("Task: iniciando análisis de proceso %s (intento %d)", proceso_id, intento_id)

    es_completo = criteria.get("tipo", "BASICO") == "COMPLETO"
    periodo = criteria.get("periodo", "2024")

    # Fase 1: Pre-filtro — buscar candidatos en Oracle (batch inserts)
    resumen = await pre_filtrar(repo, proceso_id, intento_id, criteria)

    if resumen["errores"] == 4:
        logger.error("Pre-filtro: fallaron todas las consultas de candidatos")
        await repo.actualizar_estado_proceso(
            uuid.UUID(proceso_id), "ERROR",
            total_nits=0, candidatos=0, omisos=0, exactos=0, inexactos=0,
        )
        await repo.actualizar_estado_intento(intento_id, "ERROR")
        await repo.insertar_error_proceso(
            uuid.UUID(proceso_id), intento_id, "MCP", "MCP_ALL_FAIL",
            "Fallaron todas las consultas de candidatos en el pre-filtro",
        )
        return

    if resumen["total"] == 0:
        logger.info("Pre-filtro: no se encontraron candidatos en los criterios")
        await repo.actualizar_estado_proceso(
            uuid.UUID(proceso_id), "COMPLETADO",
            total_nits=0, candidatos=0, omisos=0, exactos=0, inexactos=0,
        )
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

    candidatos = [r for r in rows if r.get("clasificacion") in ("OMISO", "INEXACTO")]

    # ── Precargar peer groups (solo para COMPLETO) ──
    grupo_ciiu: dict = {}
    if es_completo:
        grupo_ciiu = await _precargar_grupos(candidatos, periodo)

    procesados = 0
    errores = 0
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    stop_event = asyncio.Event()

    start_time = time.time()
    timeout_sec = settings.process_timeout_minutes * 60 if settings.process_timeout_minutes > 0 else 0

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
                if timeout_sec and time.time() - start_time > timeout_sec:
                    raise TimeoutError(f"Timeout de {settings.process_timeout_minutes} min alcanzado")

                contribuyente_nit = row["contribuyente_nit"]
                detalle_id = row["id"]

                # 2a. Orquestador: crosscheck + SRF + LLM (explicación IA)
                await orchestrator.ejecutar(
                    proceso_id, intento_id, contribuyente_nit, detalle_id, periodo,
                )

                if es_completo:
                    await _enriquecer_nit(detalle_id, contribuyente_nit, row.get("ciiu", ""), periodo, grupo_ciiu, proceso_id)

                async with lock:
                    procesados += 1
            except TimeoutError:
                logger.warning("Proceso %s: timeout de %d min alcanzado", proceso_id, settings.process_timeout_minutes)
                stop_event.set()
            except Exception as e:
                logger.error("Error procesando NIT %s: %s", contribuyente_nit, str(e))
                async with lock:
                    errores += 1
                await repo.insertar_error_detalle(
                    uuid.UUID(proceso_id), row["id"], row["contribuyente_nit"], "PROCESO", "ANALISIS_FAIL", str(e),
                )

    tasks = [_procesar(r) for r in rows]
    await asyncio.gather(*tasks)

    if stop_event.is_set() and not _check_cancel(proceso_id):
        # Timeout
        await repo.actualizar_progreso_intento(intento_id, procesados, errores)
        estado_final = "ERROR"
    elif stop_event.is_set():
        await repo.actualizar_estado_proceso(
            uuid.UUID(proceso_id), "INTERRUMPIDO",
            total_nits=resumen.get("total", 0),
            candidatos=resumen.get("total", 0),
            omisos=resumen.get("OMISO", 0),
            inexactos=resumen.get("INEXACTO", 0),
            exactos=resumen.get("EXACTO", 0),
        )
        await repo.actualizar_estado_intento(intento_id, "INTERRUMPIDO", error_resumen="Cancelado externamente")
        return
    else:
        estado_final = "COMPLETADO" if errores == 0 else "ERROR"

    await repo.actualizar_estado_intento(intento_id, estado_final)
    await repo.actualizar_estado_proceso(
        uuid.UUID(proceso_id), estado_final,
        total_nits=resumen.get("total", 0),
        candidatos=resumen.get("total", 0),
        omisos=resumen.get("OMISO", 0),
        inexactos=resumen.get("INEXACTO", 0),
        exactos=resumen.get("EXACTO", 0),
    )
    await repo.actualizar_progreso_intento(intento_id, procesados, errores)

    # Fase 3: Resumen ejecutivo (solo para COMPLETO)
    if es_completo and procesados > 0:
        await _generar_resumen_proceso(uuid.UUID(proceso_id), periodo, repo, LLMService())

    logger.info("Task: proceso %s completado — %d OK, %d errores", proceso_id, procesados, errores)


# ── Enriquecimiento COMPLETO ──


async def _precargar_grupos(candidatos: list[dict], periodo: str) -> dict[str, tuple]:
    ciius = {r.get("ciiu", "") for r in candidatos} - {""}
    behavioral_repo = OracleBehavioralRepository()
    grupos: dict[str, tuple] = {}

    for ciiu in ciius:
        try:
            pares_rows = await behavioral_repo.obtener_pares(periodo, ciiu, regimen=None)
            pares = [build_contributor_metrics(row, periodo) for row in pares_rows]
            benchmark = build_benchmark(pares, ciiu, "", periodo)
            grupos[ciiu] = (pares, benchmark)
        except Exception as e:
            logger.warning("No se pudo precargar grupo CIIU %s: %s", ciiu, str(e))

    return grupos


async def _enriquecer_nit(
    detalle_id: int, contribuyente_nit: str, ciiu: str, periodo: str,
    grupo_ciiu: dict[str, tuple], proceso_id: str,
) -> None:
    razones: list[str] = []
    oracle_client = None
    try:
        oracle_client = OracleClient()
        behavioral_repo = OracleBehavioralRepository()

        datos = await obtener_datos_fiscales(oracle_client, contribuyente_nit, periodo)
        if not datos:
            razones.append("Sin datos fiscales disponibles en Oracle")

        all_hallazgos: list[dict] = []

        # 1. Historial temporal
        historico = await behavioral_repo.obtener_historico_nit(contribuyente_nit)
        if not historico:
            razones.append("Sin historial comportamental")
        hallazgos_temp = analizar_patrones_temporales(historico, periodo)
        if hallazgos_temp:
            all_hallazgos.extend(hallazgos_temp)

        # 2. Reglas fiscales
        historico_bases = [
            {"periodo": h["periodo"], "base_gravable": h["base_gravable"]}
            for h in historico
        ]
        hallazgos_reglas, hallazgos_reglas_db = await _aplicar_reglas_fiscales(
            detalle_id, contribuyente_nit, periodo, datos or {}, historico_bases, proceso_id,
        )
        all_hallazgos.extend(hallazgos_reglas_db)

        # 3. Comparación comportamental
        if not ciiu or ciiu not in grupo_ciiu:
            razones.append(f"CIIU '{ciiu}' sin grupo de pares para análisis comportamental")
        resultado_comp, hallazgos_comp = await _enriquecer_con_comportamiento(
            detalle_id, contribuyente_nit, ciiu, periodo, grupo_ciiu,
        )
        all_hallazgos.extend(hallazgos_comp)

        # 4. Score unificado
        srf_total = 0.0
        if datos:
            from domain.services.crosscheck_service import calcular_srf
            srf_total = calcular_srf(datos).get("srf_total", 0)

        score_result = calcular_score_fiscal_unificado(
            analisis_comportamental=resultado_comp,
            srf_score=srf_total,
            hallazgos_reglas=hallazgos_reglas,
            hallazgos_temporales=hallazgos_temp,
        )

        # Single write: hallazgos + score en un UPDATE
        await queries.mergear_resultados_enriquecimiento(
            detalle_id, all_hallazgos, score_result.get("score_fiscal_unificado"),
        )

    except Exception as e:
        error_str = str(e)
        if "ORA-" in error_str:
            match = re.search(r"ORA-(\d+)", error_str)
            ora_code = match.group(1) if match else "???"
            ora_desc = {
                "00942": "tablas de enriquecimiento comportamental no disponibles en Oracle",
                "12541": "sin conexión a Oracle (TNS listener no disponible)",
                "01017": "credenciales Oracle inválidas",
                "12170": "timeout de conexión Oracle",
                "00001": "violación de constraint único",
            }
            desc = ora_desc.get(ora_code, f"error Oracle {ora_code}")
            razones.append(f"Error Oracle: {desc}")
        else:
            razones.append(f"Error: {error_str[:200]}")
        logger.warning("Enriquecimiento NIT %s: %s", contribuyente_nit, razones[-1])
    finally:
        if oracle_client:
            await oracle_client.close()

    if razones:
        mensaje = "; ".join(razones)
        if len(mensaje) > 500:
            mensaje = mensaje[:500] + "..."
        await queries.actualizar_estado_detalle(detalle_id, mensaje=mensaje)


async def _enriquecer_con_comportamiento(
    detalle_id: int, contribuyente_nit: str, ciiu: str, periodo: str,
    grupo_ciiu: dict[str, tuple],
) -> tuple[dict | None, list]:
    if not ciiu or ciiu not in grupo_ciiu:
        return None, []

    try:
        pares, benchmark = grupo_ciiu[ciiu]

        contribuyente = None
        for p in pares:
            if p.nit == contribuyente_nit:
                contribuyente = p
                break

        if not contribuyente:
            behavioral_repo = OracleBehavioralRepository()
            row_contrib = await behavioral_repo.obtener_contribuyente(contribuyente_nit, periodo)
            if not row_contrib:
                return None, []
            contribuyente = build_contributor_metrics(row_contrib, periodo)

        pares_sin_nit = [p for p in pares if p.nit != contribuyente_nit]
        resultado = calcular_score_comportamental(contribuyente, pares_sin_nit, benchmark)

        hallazgos = []
        if resultado.get("hallazgos"):
            hallazgos = [
                {
                    "tipo": h["tipo"],
                    "severidad": h.get("severidad"),
                    "descripcion": h.get("descripcion"),
                    "evidencia": h.get("evidencia", {}),
                    "origen": "COMPORTAMENTAL",
                }
                for h in resultado["hallazgos"]
            ]

        return resultado, hallazgos

    except Exception as e:
        logger.warning("Error en análisis comportamental NIT %s: %s", contribuyente_nit, str(e))
        return None, []


async def _aplicar_reglas_fiscales(
    detalle_id: int, contribuyente_nit: str, periodo: str,
    datos_fiscales: dict, historico_bases: list[dict],
    proceso_id: str,
) -> tuple[list[dict], list[dict]]:
    perfil = construir_perfil_fiscal_desde_datos_originales(datos_fiscales, periodo)
    perfil["historico_bases"] = historico_bases

    resultados = evaluar_reglas(perfil)
    hallazgos = []
    if resultados:
        hallazgos = [{**r, "origen": "REGLA_FISCAL"} for r in resultados]
        await _persistir_hallazgos_fiscales(proceso_id, contribuyente_nit, periodo, resultados)

    return resultados, hallazgos


async def _persistir_hallazgos_fiscales(proceso_id: str, contribuyente_nit: str, periodo: str, hallazgos: list[dict]) -> None:
    repo = PostgresProcesoRepo()
    use_case = GestionarHallazgosUseCase()
    proceso = await repo.obtener_proceso(uuid.UUID(proceso_id))
    entidad_id = proceso.get("entidad_id") if proceso else None
    for h in hallazgos:
        try:
            h["proceso_id"] = proceso_id
            h["entidad_id"] = str(entidad_id) if entidad_id else None
            await use_case.crear_hallazgo(h)
        except Exception as e:
            logger.warning("No se pudo persistir hallazgo en hallazgos_fiscales para NIT %s: %s", contribuyente_nit, e)


async def _generar_resumen_proceso(
    proceso_id: uuid.UUID, periodo: str,
    repo: PostgresProcesoRepo, llm: LLMService,
) -> None:
    try:
        max_candidatos = settings.campana_max_candidatos
        total, rows = await repo.listar_proceso_detalle(
            proceso_id=proceso_id, page=1, page_size=max_candidatos,
            ordenar_por="mcp_score", direccion="desc",
        )

        if not rows:
            return

        proceso = await repo.obtener_proceso(proceso_id)
        total_omisos = proceso.get("omisos", 0) if proceso else 0
        total_inexactos = proceso.get("inexactos", 0) if proceso else 0

        conteo_tipos: dict[str, int] = {}
        patrones_temp: dict[str, int] = {}
        for r in rows:
            hallazgos_raw = r.get("hallazgos") or []
            if isinstance(hallazgos_raw, str):
                hallazgos_raw = json.loads(hallazgos_raw)
            for h in hallazgos_raw:
                tipo = h.get("tipo", "DESCONOCIDO")
                origen = h.get("origen", "")
                conteo_tipos[tipo] = conteo_tipos.get(tipo, 0) + 1
                if origen == "TEMPORAL":
                    patrones_temp[tipo] = patrones_temp.get(tipo, 0) + 1

        top10 = rows[:10]
        top_str = "\n".join(
            f"- {r['contribuyente_nit']} ({r.get('razon_social', '')}) — score: {r.get('mcp_score', 0)}, "
            f"clasificación: {r.get('clasificacion', '')}"
            for r in top10
        )

        stats_str = "\n".join(f"- {tipo}: {count}" for tipo, count in sorted(conteo_tipos.items()))
        temp_str = "\n".join(f"- {tipo}: {count}" for tipo, count in sorted(patrones_temp.items())) or "Ninguno"

        messages = [
            {"role": "system", "content": "Eres un experto en fiscalización del ICA en Colombia."},
            {"role": "user", "content": construir_prompt(
                "resumen_campana",
                periodo=periodo,
                actividad_economica="Todas",
                total_candidatos=total,
                total_omisos=total_omisos,
                total_inexactos=total_inexactos,
                estadisticas_hallazgos=stats_str,
                top_contribuyentes=top_str,
                patrones_temporales=temp_str,
            )},
        ]

        resultado = await llm.analyze(messages)
        await queries.mergear_criteria_proceso(proceso_id, {"resumen_campana": resultado})
        logger.info("Proceso %s: resumen ejecutivo generado", proceso_id)

    except Exception as e:
        logger.warning("Proceso %s: error generando resumen — %s", proceso_id, str(e))

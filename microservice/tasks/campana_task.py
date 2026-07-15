import json
import logging
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
from infrastructure.mcp.classify import clasificar_candidato
from infrastructure.mcp.oracle_adapter import OracleClient
from infrastructure.mcp.pagination import (
    obtener_datos_fiscales,
    obtener_inexactos_ciiu,
    obtener_inexactos_retenciones,
    obtener_omisos_conocidos,
    obtener_omisos_desconocidos,
)
from infrastructure.persistence import queries
from infrastructure.persistence.repositorio_proceso import PostgresProcesoRepo

logger = logging.getLogger(__name__)


async def ejecutar_campana(
    proceso_id: str,
    intento_id: int,
    periodo: str,
    actividad_economica: str | None,
    umbral_pct: float,
):
    repo = PostgresProcesoRepo()
    pid = uuid.UUID(proceso_id)

    try:
        # ── Fase A: Descubrimiento ──
        total, omisos, inexactos = await _fase_descubrimiento(
            pid, intento_id, periodo, actividad_economica, umbral_pct, repo,
        )

        if total == 0:
            await repo.actualizar_estado_intento(intento_id, "COMPLETADO")
            await repo.actualizar_estado_proceso(pid, "COMPLETADO", total_nits=0, candidatos=0, omisos=0, inexactos=0)
            logger.info("Campaña %s: sin candidatos encontrados", proceso_id)
            return

        # ── Fase B: Análisis ──
        await _fase_analisis(pid, intento_id, periodo, actividad_economica, repo)

    except Exception as e:
        logger.error("Campaña %s: error fatal — %s", proceso_id, str(e))
        await repo.insertar_error_proceso(pid, intento_id, "PROCESO", "CAMPANA_FAIL", str(e))
        await repo.actualizar_estado_intento(intento_id, "ERROR", error_resumen=str(e))
        await repo.actualizar_estado_proceso(pid, "ERROR")


async def _fase_descubrimiento(
    proceso_id: uuid.UUID,
    intento_id: int,
    periodo: str,
    actividad_economica: str | None,
    umbral_pct: float,
    repo: PostgresProcesoRepo,
) -> tuple[int, int, int]:
    await repo.actualizar_estado_proceso(proceso_id, "PREFILTRANDO")
    await repo.actualizar_estado_intento(intento_id, "PREFILTRANDO")

    client = OracleClient()
    seen: set[str] = set()
    contadores = {"total": 0, "omisos": 0, "inexactos": 0}
    max_candidatos = settings.campana_max_candidatos

    fuentes = [
        ("OMISO_CONOCIDO", obtener_omisos_conocidos(client, vigencia=periodo, periodo=periodo)),
        ("OMISO_DESCONOCIDO", obtener_omisos_desconocidos(client, vigencia=periodo)),
        ("INEXACTO_CIIU", obtener_inexactos_ciiu(client, periodo=periodo)),
        ("INEXACTO_RETENCIONES", obtener_inexactos_retenciones(client, periodo=periodo, umbral_pct=umbral_pct)),
    ]

    for fuente, generador in fuentes:
        if contadores["total"] >= max_candidatos:
            logger.warning("Campaña %s: límite de %d candidatos alcanzado", proceso_id, max_candidatos)
            break

        async for item in generador:
            if contadores["total"] >= max_candidatos:
                break

            nit = _extraer_nit(item)
            if not nit or nit in seen:
                continue

            if actividad_economica and not _coincide_actividad(item, fuente, actividad_economica):
                continue

            seen.add(nit)
            item["tipo"] = fuente
            clasificacion, razon = clasificar_candidato(item)

            await repo.insertar_detalle(
                proceso_id,
                intento_id,
                nit=nit,
                clasificacion=clasificacion,
                razon_social=item.get("nmbre_rzon_scial") or item.get("razon_social") or "",
                ciiu=_extraer_actividad(item, fuente) or "",
                es_candidato=clasificacion != "EXACTO",
                mcp_razon=razon,
            )

            contadores["total"] += 1
            if clasificacion.startswith("OMISO"):
                contadores["omisos"] += 1
            elif clasificacion.startswith("INEXACTO"):
                contadores["inexactos"] += 1

    await repo.actualizar_estado_proceso(
        proceso_id, "PREFILTRADO_COMPLETADO",
        total_nits=contadores["total"],
        candidatos=contadores["omisos"] + contadores["inexactos"],
        omisos=contadores["omisos"],
        inexactos=contadores["inexactos"],
    )

    logger.info(
        "Campaña %s: descubrimiento completado — %d total, %d omisos, %d inexactos",
        proceso_id, contadores["total"], contadores["omisos"], contadores["inexactos"],
    )
    return contadores["total"], contadores["omisos"], contadores["inexactos"]


async def _fase_analisis(
    proceso_id: uuid.UUID,
    intento_id: int,
    periodo: str,
    actividad_economica: str | None,
    repo: PostgresProcesoRepo,
):
    await repo.actualizar_estado_proceso(proceso_id, "EN_PROCESO")
    await repo.actualizar_estado_intento(intento_id, "EN_PROCESO")

    llm = LLMService()
    orchestrator = ProcesoOrchestrator(llm, repo)
    behavioral_repo = OracleBehavioralRepository()
    oracle_client = OracleClient()

    total, rows = await repo.listar_proceso_detalle(
        proceso_id=proceso_id,
        intento_id=intento_id,
        page=1,
        page_size=settings.campana_max_candidatos,
    )

    candidatos = [r for r in rows if r.get("clasificacion", "EXACTO") != "EXACTO"]

    # ── Precargar pares por CIIU (una query por CIIU distinto) ──
    grupo_ciiu = await _precargar_grupos(candidatos, periodo)

    procesados = 0
    errores = 0
    start_time = time.time()
    timeout_sec = settings.process_timeout_minutes * 60

    for row in candidatos:
        try:
            if settings.process_timeout_minutes > 0 and time.time() - start_time > timeout_sec:
                logger.warning("Campana %s: timeout de %d min alcanzado", proceso_id, settings.process_timeout_minutes)
                raise TimeoutError(f"Timeout de {settings.process_timeout_minutes} min alcanzado")

            from tasks.concurrency import esta_activo as _check_cancel
            if not _check_cancel(str(proceso_id)):
                logger.warning("Campana %s: cancelada externamente", proceso_id)
                await repo.actualizar_estado_proceso(proceso_id, "INTERRUMPIDO")
                await repo.actualizar_estado_intento(intento_id, "INTERRUMPIDO", error_resumen="Cancelado externamente")
                return

            nit = row["nit"]
            detalle_id = row["id"]
            ciiu = row.get("ciiu", "")

            # 1. Obtener datos fiscales (compartido con orquestador)
            datos = await obtener_datos_fiscales(oracle_client, nit, periodo)

            # 2. Orquestador: crosscheck + SRF + LLM
            await orchestrator.ejecutar(
                str(proceso_id), intento_id, nit, detalle_id, periodo, datos,
            )

            # 3. F1: Historial temporal
            historico = await behavioral_repo.obtener_historico_nit(nit)
            hallazgos_temp = analizar_patrones_temporales(historico, periodo)
            if hallazgos_temp:
                await queries.mergear_hallazgos_detalle(detalle_id, hallazgos_temp)

            # 4. F2: Reglas fiscales (usa historial para R10)
            historico_bases = [
                {"periodo": h["periodo"], "base_gravable": h["base_gravable"]}
                for h in historico
            ]
            hallazgos_reglas = await _aplicar_reglas_fiscales(
                detalle_id, nit, periodo, datos or {}, historico_bases,
            )

            # 5. Comparación comportamental
            resultado_comp = await _enriquecer_con_comportamiento(
                detalle_id, nit, ciiu, periodo, grupo_ciiu,
            )

            # 6. F3: Score unificado
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
            await queries.actualizar_score_detalle(detalle_id, score_result["score_fiscal_unificado"])

            procesados += 1
        except Exception as e:
            logger.error("Campaña %s: error procesando NIT %s — %s", proceso_id, row["nit"], str(e))
            errores += 1
            await repo.insertar_error_detalle(
                proceso_id, row["id"], row["nit"], "PROCESO", "ANALISIS_FAIL", str(e),
            )

        await repo.actualizar_progreso_intento(intento_id, procesados, errores)

    # 7. F4: Resumen ejecutivo de la campaña
    await _generar_resumen_campana(proceso_id, periodo, actividad_economica, repo, llm)

    estado_final = "COMPLETADO" if errores == 0 else "ERROR"
    await repo.actualizar_estado_intento(intento_id, estado_final)
    await repo.actualizar_estado_proceso(proceso_id, estado_final)

    logger.info("Campaña %s: análisis completado — %d OK, %d errores", proceso_id, procesados, errores)


async def _precargar_grupos(
    candidatos: list[dict],
    periodo: str,
) -> dict[str, tuple[list, object]]:
    ciius = {r.get("ciiu", "") for r in candidatos} - {""}
    behavioral_repo = OracleBehavioralRepository()
    grupos: dict[str, tuple[list, object]] = {}

    for ciiu in ciius:
        pares_rows = await behavioral_repo.obtener_pares(periodo, ciiu, regimen=None)
        pares = [build_contributor_metrics(row, periodo) for row in pares_rows]
        benchmark = build_benchmark(pares, ciiu, "", periodo)
        grupos[ciiu] = (pares, benchmark)
        logger.info(
            "Grupo CIIU %s: %d pares, mediana base $%s",
            ciiu, benchmark.total_pares, benchmark.mediana_base_gravable,
        )

    return grupos


async def _enriquecer_con_comportamiento(
    detalle_id: int,
    nit: str,
    ciiu: str,
    periodo: str,
    grupo_ciiu: dict[str, tuple[list, object]],
) -> dict | None:
    if not ciiu or ciiu not in grupo_ciiu:
        return None

    try:
        pares, benchmark = grupo_ciiu[ciiu]

        contribuyente = None
        for p in pares:
            if p.nit == nit:
                contribuyente = p
                break

        if not contribuyente:
            behavioral_repo = OracleBehavioralRepository()
            row_contrib = await behavioral_repo.obtener_contribuyente(nit, periodo)
            if not row_contrib:
                return None
            contribuyente = build_contributor_metrics(row_contrib, periodo)

        pares_sin_nit = [p for p in pares if p.nit != nit]
        resultado = calcular_score_comportamental(contribuyente, pares_sin_nit, benchmark)

        if resultado.get("hallazgos"):
            hallazgos_comportamentales = [
                {
                    "tipo": h["tipo"],
                    "severidad": h.get("severidad"),
                    "descripcion": h.get("descripcion"),
                    "evidencia": h.get("evidencia", {}),
                    "origen": "COMPORTAMENTAL",
                }
                for h in resultado["hallazgos"]
            ]
            await queries.mergear_hallazgos_detalle(detalle_id, hallazgos_comportamentales)

        return resultado

    except Exception as e:
        logger.warning("Campaña: error en análisis comportamental NIT %s — %s", nit, str(e))
        return None


async def _aplicar_reglas_fiscales(
    detalle_id: int,
    nit: str,
    periodo: str,
    datos_fiscales: dict,
    historico_bases: list[dict],
) -> list[dict]:
    perfil = construir_perfil_fiscal_desde_datos_originales(datos_fiscales, periodo)
    perfil["historico_bases"] = historico_bases

    resultados = evaluar_reglas(perfil)
    if resultados:
        hallazgos = [{**r, "origen": "REGLA_FISCAL"} for r in resultados]
        await queries.mergear_hallazgos_detalle(detalle_id, hallazgos)
        await _persistir_hallazgos_fiscales(nit, periodo, resultados)

    return resultados


async def _persistir_hallazgos_fiscales(nit: str, periodo: str, hallazgos: list[dict]) -> None:
    use_case = GestionarHallazgosUseCase()
    for h in hallazgos:
        try:
            await use_case.crear_hallazgo(h)
        except Exception as e:
            logger.warning("No se pudo persistir hallazgo en hallazgos_fiscales para NIT %s: %s", nit, e)


async def _generar_resumen_campana(
    proceso_id: uuid.UUID,
    periodo: str,
    actividad_economica: str | None,
    repo: PostgresProcesoRepo,
    llm: LLMService,
):
    try:
        total, rows = await repo.listar_proceso_detalle(
            proceso_id=proceso_id, page=1, page_size=settings.campana_max_candidatos,
            ordenar_por="mcp_score", direccion="desc",
        )

        if not rows:
            return

        proceso = await repo.obtener_proceso(proceso_id)
        total_omisos = proceso.get("omisos", 0) if proceso else 0
        total_inexactos = proceso.get("inexactos", 0) if proceso else 0

        # Estadísticas de hallazgos
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

        # Top 10
        top10 = rows[:10]
        top_str = "\n".join(
            f"- {r['nit']} ({r.get('razon_social', '')}) — score: {r.get('mcp_score', 0)}, "
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
                actividad_economica=actividad_economica or "Todas",
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
        logger.info("Campaña %s: resumen ejecutivo generado", proceso_id)

    except Exception as e:
        logger.warning("Campaña %s: error generando resumen — %s", proceso_id, str(e))


def _extraer_nit(item: dict) -> str:
    return item.get("idntfccion") or item.get("nit") or ""


def _extraer_actividad(item: dict, fuente: str) -> str | None:
    if fuente == "OMISO_CONOCIDO":
        return item.get("id_actvdad_ecnmca")
    if fuente == "OMISO_DESCONOCIDO":
        return item.get("ciiu")
    if fuente == "INEXACTO_CIIU":
        return item.get("ciiu_declarado") or item.get("ciiu_dian")
    return None


def _coincide_actividad(item: dict, fuente: str, filtro: str) -> bool:
    actividad = _extraer_actividad(item, fuente)
    if actividad is None:
        return fuente == "INEXACTO_RETENCIONES"
    return actividad == filtro

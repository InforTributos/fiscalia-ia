from __future__ import annotations

from datetime import UTC, datetime

from domain.fiscal.unified_score import calcular_score_fiscal_unificado


def construir_expediente_fiscal(grafo_riesgo: dict) -> dict:
    analisis = grafo_riesgo.get("analisis_comportamental") or {}
    resumen_red = grafo_riesgo.get("resumen_red") or {}
    score = calcular_score_fiscal_unificado(analisis, resumen_red)
    metricas = analisis.get("metricas") or {}
    benchmark = analisis.get("benchmark") or {}
    hallazgos = analisis.get("hallazgos") or []

    acciones = _acciones(score["prioridad"], hallazgos, resumen_red)
    evidencia = _evidencia(metricas, benchmark, hallazgos, resumen_red)
    resumen = _resumen(grafo_riesgo, score, evidencia)

    return {
        "contribuyente_nit": grafo_riesgo.get("contribuyente_nit", ""),
        "periodo": grafo_riesgo.get("periodo", ""),
        "generado_en": datetime.now(UTC).isoformat(),
        "score": score,
        "resumen_ejecutivo": resumen,
        "evidencia": evidencia,
        "acciones_sugeridas": acciones,
        "grafo": {
            "total_nodos": len(grafo_riesgo.get("nodes") or []),
            "total_relaciones": len(grafo_riesgo.get("edges") or []),
            "resumen_red": resumen_red,
        },
        "analisis_comportamental": analisis,
    }


def expediente_to_markdown(expediente: dict) -> str:
    score = expediente["score"]
    lines = [
        f"# Expediente Fiscal - NIT {expediente['contribuyente_nit']}",
        "",
        f"Periodo: {expediente['periodo']}",
        f"Prioridad: {score['prioridad']}",
        f"Score fiscal unificado: {score['score_fiscal_unificado']}",
        "",
        "## Resumen ejecutivo",
        expediente["resumen_ejecutivo"],
        "",
        "## Evidencia clave",
    ]
    for item in expediente["evidencia"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Acciones sugeridas"])
    for item in expediente["acciones_sugeridas"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def _resumen(grafo_riesgo: dict, score: dict, evidencia: list[str]) -> str:
    contribuyente_nit = grafo_riesgo.get("contribuyente_nit", "")
    prioridad = score["prioridad"]
    principales = "; ".join(evidencia[:3]) if evidencia else "sin evidencia material"
    return (
        f"El contribuyente {contribuyente_nit} queda clasificado con prioridad {prioridad}. "
        f"La seleccion se soporta en: {principales}."
    )


def _evidencia(metricas: dict, benchmark: dict, hallazgos: list[dict], resumen_red: dict) -> list[str]:
    evidencia = []
    if metricas and benchmark:
        evidencia.append(
            "Base gravable declarada "
            f"{metricas.get('base_gravable', 0)} frente a mediana sectorial "
            f"{benchmark.get('mediana_base_gravable', 0)}"
        )
        if metricas.get("ratio_exogena_declarado") is not None:
            evidencia.append(f"Relacion exogena/declarado: {metricas.get('ratio_exogena_declarado')}")
    for hallazgo in hallazgos[:5]:
        evidencia.append(f"{hallazgo.get('tipo')}: {hallazgo.get('descripcion')}")
    if resumen_red.get("empresas_conectadas", 0):
        evidencia.append(
            f"Conecta con {resumen_red.get('empresas_conectadas')} empresa(s) por atributos compartidos"
        )
    return evidencia or ["No se encontro evidencia suficiente para priorizacion automatica"]


def _acciones(prioridad: str, hallazgos: list[dict], resumen_red: dict) -> list[str]:
    acciones = []
    if prioridad in ("CRITICA", "ALTA"):
        acciones.append("Abrir revision prioritaria y validar soportes de ingresos declarados")
        acciones.append("Cruzar declaracion ICA contra exogena y soportes contables del periodo")
    if resumen_red.get("empresas_conectadas", 0):
        acciones.append("Revisar empresas conectadas antes de actuar sobre el caso de forma aislada")
    if any(h.get("tipo", "").startswith("EXOGENA") for h in hallazgos):
        acciones.append("Solicitar explicacion de diferencias entre ingresos exogenos y base declarada")
    return acciones or ["Mantener en monitoreo y revisar si aparecen nuevos hallazgos"]


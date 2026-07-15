from __future__ import annotations

REQUIRED_EVIDENCE_BY_FORCE = {
    "DIRECTA": 1,
    "MEDIA": 2,
    "INDICIARIA": 2,
}


def revisar_hallazgo_deterministico(hallazgo: dict) -> dict:
    evidencias = hallazgo.get("evidencias") or []
    fuerza = str(hallazgo.get("fuerza_probatoria") or "INDICIARIA").upper()
    score = float(hallazgo.get("score") or 0)
    accionable = bool(hallazgo.get("accionable"))
    brecha = float(hallazgo.get("brecha_valor") or 0)
    impuesto = float(hallazgo.get("impuesto_estimado") or 0)

    riesgos = []
    faltantes = []
    preguntas = []

    min_evidencias = REQUIRED_EVIDENCE_BY_FORCE.get(fuerza, 2)
    if len(evidencias) < min_evidencias:
        faltantes.append(f"Agregar al menos {min_evidencias} evidencia(s) para fuerza probatoria {fuerza}.")
    if not accionable:
        riesgos.append("La ventana legal no esta vigente; revisar antes de asignar al fiscalizador.")
    if brecha <= 0 and impuesto <= 0:
        faltantes.append("Cuantificar brecha o impuesto estimado para priorizacion economica.")
    if fuerza == "INDICIARIA":
        riesgos.append("Hallazgo indiciario: requiere corroboracion antes de soportar actuacion formal.")
        preguntas.append("Que fuente independiente confirma la senal estadistica o de grafo?")
    if score >= 80 and not evidencias:
        riesgos.append("Score alto sin evidencia persistida; no debe avanzar sin soporte documental.")

    completitud = _calcular_completitud(hallazgo, evidencias, faltantes, riesgos)
    return {
        "agente": "revisor_hallazgos",
        "version": "1.0",
        "completitud": completitud,
        "estado_revision": _estado_revision(completitud, riesgos, faltantes),
        "riesgos": riesgos,
        "evidencia_faltante": faltantes,
        "preguntas": preguntas or ["No se requieren preguntas adicionales con la informacion actual."],
        "accion_recomendada": _accion_recomendada(completitud, riesgos, faltantes, score),
        "resumen": _resumen(completitud, riesgos, faltantes),
    }


def fusionar_revision_ia(base: dict, ia: dict) -> dict:
    if ia.get("modo_degradado"):
        return {**base, "ia_disponible": False, "ia_error": ia.get("error", "")}
    return {
        **base,
        "ia_disponible": True,
        "comentario_ia": ia.get("comentario", ia.get("explicacion", "")),
        "riesgos_ia": ia.get("riesgos", []),
        "preguntas_ia": ia.get("preguntas", []),
    }


def _calcular_completitud(hallazgo: dict, evidencias: list[dict], faltantes: list[str], riesgos: list[str]) -> int:
    score = 100
    if not evidencias:
        score -= 35
    score -= min(len(faltantes) * 15, 45)
    score -= min(len(riesgos) * 10, 30)
    if not hallazgo.get("resumen"):
        score -= 10
    if not hallazgo.get("accionable"):
        score -= 25
    return max(score, 0)


def _estado_revision(completitud: int, riesgos: list[str], faltantes: list[str]) -> str:
    if completitud >= 80 and not faltantes:
        return "COMPLETO"
    if completitud >= 55:
        return "REQUIERE_AJUSTES"
    return "INCOMPLETO"


def _accion_recomendada(completitud: int, riesgos: list[str], faltantes: list[str], score: float) -> str:
    if completitud >= 80 and score >= 80:
        return "Pasar a revision humana prioritaria."
    if completitud >= 80:
        return "Pasar a cola de revision humana."
    if faltantes:
        return "Completar evidencia antes de asignar al fiscalizador."
    if riesgos:
        return "Revisar riesgos juridicos antes de avanzar."
    return "Mantener en monitoreo."


def _resumen(completitud: int, riesgos: list[str], faltantes: list[str]) -> str:
    return (
        f"Revision automatica con completitud {completitud}%. "
        f"Riesgos: {len(riesgos)}. Evidencias faltantes: {len(faltantes)}."
    )


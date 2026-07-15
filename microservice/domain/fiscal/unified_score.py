from __future__ import annotations

PROBATORIA_SCORE = {"DIRECTA": 100, "MEDIA": 65, "INDICIARIA": 35}


def calcular_score_fiscal_unificado(
    analisis_comportamental: dict | None = None,
    resumen_red: dict | None = None,
    srf_score: float = 0.0,
    hallazgos_reglas: list[dict] | None = None,
    hallazgos_temporales: list[dict] | None = None,
) -> dict:
    analisis_comportamental = analisis_comportamental or {}
    resumen_red = resumen_red or {}
    hallazgos_reglas = hallazgos_reglas or []
    hallazgos_temporales = hallazgos_temporales or []

    score_comportamental = float(analisis_comportamental.get("score_comportamental") or 0)
    score_red = float(resumen_red.get("score_red") or 0)
    confianza = float(analisis_comportamental.get("confianza") or 0)
    hallazgos_comp = analisis_comportamental.get("hallazgos") or []

    score_reglas = _score_reglas(hallazgos_reglas)
    score_temporal = _score_temporal(hallazgos_temporales)

    score = (
        score_comportamental * 0.30
        + srf_score * 0.20
        + score_reglas * 0.20
        + score_red * 0.15
        + score_temporal * 0.10
        + confianza * 100 * 0.05
    )

    if resumen_red.get("empresas_conectadas", 0) >= 3 and score_comportamental >= 70:
        score += 5
    if any(h.get("tipo") == "EXOGENA_CON_DECLARACION_CERO" for h in hallazgos_comp):
        score += 8
    if any(h.get("fuerza_probatoria") == "DIRECTA" for h in hallazgos_reglas):
        score += 10
    if any(h.get("tipo") == "DESAPARICION_DECLARATIVA" for h in hallazgos_temporales):
        score += 5

    score = min(round(score, 2), 100.0)
    return {
        "score_fiscal_unificado": score,
        "prioridad": _prioridad(score),
        "componentes": {
            "score_comportamental": round(score_comportamental, 2),
            "score_srf": round(srf_score, 2),
            "score_reglas": round(score_reglas, 2),
            "score_red": round(score_red, 2),
            "score_temporal": round(score_temporal, 2),
            "confianza": confianza,
        },
        "criterios": _criterios(
            score, analisis_comportamental, resumen_red, hallazgos_reglas, hallazgos_temporales,
        ),
    }


def _score_severidad(hallazgos: list[dict]) -> float:
    if not hallazgos:
        return 0.0
    values = {"ALTA": 100, "MEDIA": 65, "BAJA": 35}
    return min(sum(values.get(h.get("severidad"), 25) for h in hallazgos) / max(len(hallazgos), 1), 100)


def _prioridad(score: float) -> str:
    if score >= 90:
        return "CRITICA"
    if score >= 75:
        return "ALTA"
    if score >= 50:
        return "MEDIA"
    return "BAJA"


def _score_reglas(hallazgos: list[dict]) -> float:
    if not hallazgos:
        return 0.0
    total = 0.0
    for h in hallazgos:
        prob = PROBATORIA_SCORE.get(h.get("fuerza_probatoria", ""), 25)
        brecha = min(float(h.get("brecha_valor") or 0) / 100_000_000 * 100, 100)
        total += (prob * 0.6 + brecha * 0.4)
    return min(total / len(hallazgos), 100.0)


def _score_temporal(hallazgos: list[dict]) -> float:
    if not hallazgos:
        return 0.0
    return min(_score_severidad(hallazgos) + len(hallazgos) * 10, 100.0)


def _criterios(
    score: float, analisis: dict, resumen_red: dict,
    hallazgos_reglas: list[dict] | None = None,
    hallazgos_temporales: list[dict] | None = None,
) -> list[str]:
    criterios = []
    if analisis.get("score_comportamental", 0) >= 75:
        criterios.append("Comportamiento fiscal atipico frente al grupo comparable")
    if resumen_red.get("bonus_red", 0) > 0:
        criterios.append("Conexiones de red aumentan la prioridad del caso")
    if resumen_red.get("empresas_conectadas", 0) >= 3:
        criterios.append("Varias empresas conectadas al contribuyente objetivo")
    if hallazgos_reglas:
        tipos = {h.get("regla", "") for h in hallazgos_reglas}
        criterios.append(f"Reglas fiscales activadas: {', '.join(sorted(tipos))}")
    if hallazgos_temporales:
        criterios.append("Patrones temporales anomalos detectados en el historial")
    if score >= 90:
        criterios.append("Caso candidato para revision prioritaria inmediata")
    return criterios or ["Sin criterios de criticidad material con la informacion disponible"]


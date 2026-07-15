from __future__ import annotations

from datetime import date

PROBATORIA_SCORE = {
    "DIRECTA": 100,
    "MEDIA": 60,
    "INDICIARIA": 30,
}


def calcular_score_hallazgo(
    fuerza_probatoria: str,
    impuesto_estimado: float,
    dias_restantes: int,
    reincidencia: int = 0,
    corroboracion: int = 1,
) -> dict:
    p = PROBATORIA_SCORE.get(fuerza_probatoria.upper(), 30)
    m = _score_monto(impuesto_estimado)
    u = _score_urgencia(dias_restantes)
    r = min(reincidencia * 25, 100)
    c = min(corroboracion * 25, 100)
    score = round(0.35 * p + 0.30 * m + 0.15 * u + 0.10 * r + 0.10 * c, 2)
    return {
        "score": min(score, 100.0),
        "componentes": {
            "fuerza_probatoria": p,
            "monto": m,
            "urgencia": u,
            "reincidencia": r,
            "corroboracion": c,
            "fecha_calculo": date.today().isoformat(),
        },
        "banda": banda(score),
    }


def banda(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    return "D"


def _score_monto(impuesto_estimado: float) -> float:
    if impuesto_estimado <= 0:
        return 0.0
    return min(round(impuesto_estimado / 100_000_000 * 100, 2), 100.0)


def _score_urgencia(dias_restantes: int) -> float:
    if dias_restantes < 0:
        return 0.0
    if dias_restantes <= 180:
        return 100.0
    if dias_restantes <= 365:
        return 75.0
    if dias_restantes <= 730:
        return 45.0
    return 20.0


from __future__ import annotations

from statistics import mean, stdev

from domain.behavioral.indicators import to_float


def analizar_patrones_temporales(
    historico: list[dict],
    periodo_actual: str,
    umbral_caida: float = 0.60,
    periodos_tendencia: int = 3,
    umbral_volatilidad: float = 0.50,
) -> list[dict]:
    series = sorted(historico, key=lambda x: str(x.get("periodo", "")))
    if len(series) < 2:
        return []

    hallazgos = []
    for detector in [
        lambda: _detectar_caida_abrupta(series, umbral_caida),
        lambda: _detectar_tendencia_descendente(series, periodos_tendencia),
        lambda: _detectar_divergencia_exogena(series),
        lambda: _detectar_volatilidad(series, umbral_volatilidad),
        lambda: _detectar_desaparicion(series, periodo_actual),
    ]:
        resultado = detector()
        if resultado:
            hallazgos.append(resultado)

    return hallazgos


def _detectar_caida_abrupta(series: list[dict], umbral: float) -> dict | None:
    if len(series) < 2:
        return None
    anterior = to_float(series[-2].get("base_gravable"))
    actual = to_float(series[-1].get("base_gravable"))
    if anterior <= 0:
        return None
    caida_pct = (anterior - actual) / anterior
    if caida_pct < umbral:
        return None
    return {
        "tipo": "CAIDA_ABRUPTA_TEMPORAL",
        "severidad": "ALTA",
        "descripcion": (
            f"La base gravable cayó {caida_pct:.0%} entre "
            f"{series[-2]['periodo']} (${anterior:,.0f}) y {series[-1]['periodo']} (${actual:,.0f})."
        ),
        "evidencia": {
            "periodo_anterior": series[-2]["periodo"],
            "base_anterior": anterior,
            "periodo_actual": series[-1]["periodo"],
            "base_actual": actual,
            "caida_pct": round(caida_pct * 100, 1),
        },
        "origen": "TEMPORAL",
    }


def _detectar_tendencia_descendente(series: list[dict], n: int) -> dict | None:
    if len(series) < n:
        return None
    ultimos = series[-n:]
    bases = [to_float(p.get("base_gravable")) for p in ultimos]
    if bases[0] <= 0:
        return None
    for i in range(1, len(bases)):
        if bases[i] >= bases[i - 1]:
            return None
    caida_total_pct = (bases[0] - bases[-1]) / bases[0] * 100
    return {
        "tipo": "TENDENCIA_DESCENDENTE",
        "severidad": "ALTA" if caida_total_pct > 50 else "MEDIA",
        "descripcion": (
            f"Base gravable en descenso durante {n} periodos consecutivos "
            f"(caída acumulada del {caida_total_pct:.0f}%)."
        ),
        "evidencia": {
            "periodos": [p["periodo"] for p in ultimos],
            "bases": bases,
            "caida_total_pct": round(caida_total_pct, 1),
        },
        "origen": "TEMPORAL",
    }


def _detectar_divergencia_exogena(series: list[dict]) -> dict | None:
    if len(series) < 3:
        return None
    mitad = len(series) // 2
    primera = series[:mitad]
    segunda = series[mitad:]

    avg_exo_1 = mean([to_float(p.get("ingresos_exogena")) for p in primera]) or 1
    avg_exo_2 = mean([to_float(p.get("ingresos_exogena")) for p in segunda])
    avg_base_1 = mean([to_float(p.get("base_gravable")) for p in primera]) or 1
    avg_base_2 = mean([to_float(p.get("base_gravable")) for p in segunda])

    crec_exogena = (avg_exo_2 - avg_exo_1) / avg_exo_1
    crec_base = (avg_base_2 - avg_base_1) / avg_base_1

    if crec_exogena <= 0.10 or crec_base >= crec_exogena * 0.5:
        return None

    return {
        "tipo": "DIVERGENCIA_EXOGENA_CRECIENTE",
        "severidad": "ALTA" if crec_exogena > 0.30 and crec_base < 0 else "MEDIA",
        "descripcion": (
            f"Ingresos exógena crecieron {crec_exogena:.0%} pero la base gravable "
            f"{'cayó' if crec_base < 0 else 'apenas creció'} {crec_base:.0%}."
        ),
        "evidencia": {
            "crecimiento_exogena_pct": round(crec_exogena * 100, 1),
            "crecimiento_base_pct": round(crec_base * 100, 1),
            "promedio_exogena_reciente": round(avg_exo_2, 2),
            "promedio_base_reciente": round(avg_base_2, 2),
        },
        "origen": "TEMPORAL",
    }


def _detectar_volatilidad(series: list[dict], umbral_cv: float) -> dict | None:
    if len(series) < 4:
        return None
    bases = [to_float(p.get("base_gravable")) for p in series]
    positivos = [b for b in bases if b > 0]
    if len(positivos) < 3:
        return None
    avg = mean(positivos)
    if avg <= 0:
        return None
    cv = stdev(positivos) / avg
    if cv < umbral_cv:
        return None
    return {
        "tipo": "VOLATILIDAD_SOSPECHOSA",
        "severidad": "MEDIA",
        "descripcion": (
            f"La base gravable muestra alta variabilidad entre periodos "
            f"(coeficiente de variación: {cv:.2f})."
        ),
        "evidencia": {
            "coeficiente_variacion": round(cv, 4),
            "periodos": [p["periodo"] for p in series],
            "bases": bases,
        },
        "origen": "TEMPORAL",
    }


def _detectar_desaparicion(series: list[dict], periodo_actual: str) -> dict | None:
    periodos_presentes = {str(p.get("periodo", "")) for p in series}
    if periodo_actual in periodos_presentes:
        return None
    periodos_con_base = [
        p for p in series
        if to_float(p.get("base_gravable")) > 0
    ]
    if not periodos_con_base:
        return None
    ultimo_periodo = periodos_con_base[-1]
    return {
        "tipo": "DESAPARICION_DECLARATIVA",
        "severidad": "ALTA",
        "descripcion": (
            f"El contribuyente declaró hasta {ultimo_periodo['periodo']} "
            f"pero no tiene declaración en {periodo_actual}."
        ),
        "evidencia": {
            "ultimo_periodo_declarado": ultimo_periodo["periodo"],
            "ultima_base_gravable": to_float(ultimo_periodo.get("base_gravable")),
            "periodo_sin_declaracion": periodo_actual,
            "periodos_historicos": len(periodos_con_base),
        },
        "origen": "TEMPORAL",
    }

from __future__ import annotations

from dataclasses import asdict

from domain.behavioral.indicators import iqr_bounds, percentile_rank, robust_zscore
from domain.behavioral.peer_group import ContributorMetrics, PeerBenchmark


def _add_hallazgo(hallazgos: list[dict], tipo: str, severidad: str, descripcion: str, evidencia: dict):
    hallazgos.append({
        "tipo": tipo,
        "severidad": severidad,
        "descripcion": descripcion,
        "evidencia": evidencia,
    })


def _prioridad(score: float) -> str:
    if score >= 80:
        return "ALTA"
    if score >= 55:
        return "MEDIA"
    return "BAJA"


def _confianza(total_pares: int) -> float:
    if total_pares >= 100:
        return 0.9
    if total_pares >= 30:
        return 0.75
    if total_pares >= 10:
        return 0.6
    return 0.4


def calcular_score_comportamental(
    contribuyente: ContributorMetrics,
    pares: list[ContributorMetrics],
    benchmark: PeerBenchmark,
    min_pares: int = 10,
) -> dict:
    bases = [p.base_gravable for p in pares if p.base_gravable > 0]
    percentil_base = percentile_rank(bases, contribuyente.base_gravable)
    z_base = robust_zscore(bases, contribuyente.base_gravable)
    limite_inf, _ = iqr_bounds(bases)
    mediana = benchmark.mediana_base_gravable
    variacion_mediana_pct = round((contribuyente.base_gravable - mediana) / mediana * 100, 2) if mediana else 0.0

    score = 0.0
    hallazgos: list[dict] = []

    if benchmark.total_pares < min_pares:
        _add_hallazgo(
            hallazgos,
            "MUESTRA_COMPARABLE_BAJA",
            "BAJA",
            "El grupo comparable tiene pocos contribuyentes; el resultado debe usarse como alerta preliminar.",
            {"total_pares": benchmark.total_pares, "min_pares": min_pares},
        )

    if bases and contribuyente.base_gravable <= benchmark.p10_base_gravable:
        score += 30
        _add_hallazgo(
            hallazgos,
            "BASE_GRAVABLE_BAJO_P10",
            "ALTA",
            "La base gravable declarada está en el 10% inferior del grupo comparable.",
            {"base_gravable": contribuyente.base_gravable, "p10_sector": benchmark.p10_base_gravable},
        )
    elif bases and contribuyente.base_gravable <= benchmark.p25_base_gravable:
        score += 18
        _add_hallazgo(
            hallazgos,
            "BASE_GRAVABLE_BAJO_P25",
            "MEDIA",
            "La base gravable declarada está por debajo del primer cuartil del grupo comparable.",
            {"base_gravable": contribuyente.base_gravable, "p25_sector": benchmark.p25_base_gravable},
        )

    if mediana and variacion_mediana_pct <= -70:
        score += 25
        _add_hallazgo(
            hallazgos,
            "SUBDECLARACION_RELATIVA_SECTOR",
            "ALTA",
            "La base gravable está muy por debajo de la mediana de empresas con actividad similar.",
            {"variacion_mediana_pct": variacion_mediana_pct, "mediana_sector": mediana},
        )
    elif mediana and variacion_mediana_pct <= -50:
        score += 15
        _add_hallazgo(
            hallazgos,
            "DESVIACION_RELEVANTE_SECTOR",
            "MEDIA",
            "La base gravable está significativamente por debajo de la mediana del grupo comparable.",
            {"variacion_mediana_pct": variacion_mediana_pct, "mediana_sector": mediana},
        )

    ratio = contribuyente.ratio_exogena_declarado
    if contribuyente.base_gravable <= 0 and contribuyente.ingresos_exogena > 0:
        score += 35
        _add_hallazgo(
            hallazgos,
            "EXOGENA_CON_DECLARACION_CERO",
            "ALTA",
            "Existen ingresos reportados por exógena, pero la base gravable declarada es cero.",
            {"ingresos_exogena": contribuyente.ingresos_exogena, "base_gravable": contribuyente.base_gravable},
        )
    elif ratio is not None and ratio >= 3:
        score += 25
        _add_hallazgo(
            hallazgos,
            "EXOGENA_ALTA_DECLARACION_BAJA",
            "ALTA",
            "Los ingresos de exógena superan ampliamente la base gravable declarada.",
            {"ratio_exogena_declarado": round(ratio, 4)},
        )
    elif ratio is not None and ratio >= 2:
        score += 15
        _add_hallazgo(
            hallazgos,
            "EXOGENA_SUPERA_DECLARACION",
            "MEDIA",
            "Los ingresos de exógena duplican o superan la base gravable declarada.",
            {"ratio_exogena_declarado": round(ratio, 4)},
        )

    if (
        contribuyente.tarifa_efectiva is not None
        and benchmark.mediana_tarifa_efectiva > 0
        and contribuyente.tarifa_efectiva < benchmark.mediana_tarifa_efectiva * 0.5
    ):
        score += 10
        _add_hallazgo(
            hallazgos,
            "TARIFA_EFECTIVA_ATIPICA",
            "MEDIA",
            "La tarifa efectiva está muy por debajo de la mediana del grupo comparable.",
            {
                "tarifa_efectiva": round(contribuyente.tarifa_efectiva, 6),
                "mediana_tarifa_efectiva": benchmark.mediana_tarifa_efectiva,
            },
        )

    if bases and z_base <= -2.5:
        score += 10
        _add_hallazgo(
            hallazgos,
            "OUTLIER_INFERIOR_GRUPO_COMPARABLE",
            "MEDIA",
            "La base gravable es un outlier inferior frente al comportamiento histórico del grupo.",
            {"zscore_robusto": z_base, "limite_iqr_inferior": round(limite_inf, 2)},
        )

    score = min(round(score, 2), 100.0)
    return {
        "contribuyente_nit": contribuyente.contribuyente_nit,
        "razon_social": contribuyente.razon_social,
        "ciiu": contribuyente.ciiu,
        "regimen": contribuyente.regimen,
        "vigencia": contribuyente.vigencia,
        "score_comportamental": score,
        "prioridad": _prioridad(score),
        "confianza": _confianza(benchmark.total_pares),
        "metricas": asdict(contribuyente),
        "benchmark": asdict(benchmark),
        "desviaciones": {
            "percentil_base_gravable": percentil_base,
            "variacion_mediana_base_pct": variacion_mediana_pct,
            "zscore_robusto_base": z_base,
            "outlier_iqr_inferior": contribuyente.base_gravable < limite_inf if bases else False,
        },
        "hallazgos": hallazgos,
        "explicacion": _explicar(score, hallazgos, benchmark),
    }


def _explicar(score: float, hallazgos: list[dict], benchmark: PeerBenchmark) -> str:
    if not hallazgos:
        return "No se observan desviaciones materiales frente al grupo comparable con la informacion disponible."
    tipos = ", ".join(h["tipo"] for h in hallazgos[:3])
    return (
        f"Score comportamental {score:.2f}. Se identificaron alertas {tipos} "
        f"contra {benchmark.total_pares} pares del CIIU {benchmark.ciiu}."
    )


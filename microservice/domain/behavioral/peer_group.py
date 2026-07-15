from __future__ import annotations

from dataclasses import dataclass

from domain.behavioral.indicators import median, percentile, safe_ratio, to_float


@dataclass(frozen=True)
class ContributorMetrics:
    nit: str
    razon_social: str
    ciiu: str
    regimen: str
    vigencia: str
    base_gravable: float
    impuesto: float
    ingresos_exogena: float
    tarifa_efectiva: float | None
    ratio_exogena_declarado: float | None


@dataclass(frozen=True)
class PeerBenchmark:
    ciiu: str
    regimen: str
    vigencia: str
    total_pares: int
    mediana_base_gravable: float
    p10_base_gravable: float
    p25_base_gravable: float
    p75_base_gravable: float
    p90_base_gravable: float
    mediana_tarifa_efectiva: float
    mediana_ratio_exogena_declarado: float


def build_contributor_metrics(row: dict, vigencia: str) -> ContributorMetrics:
    base = to_float(row.get("base_gravable"))
    impuesto = to_float(row.get("impuesto"))
    exogena = to_float(row.get("ingresos_exogena", row.get("ingresos")))
    return ContributorMetrics(
        nit=str(row.get("nit", "")),
        razon_social=str(row.get("razon_social", "")),
        ciiu=str(row.get("ciiu", "")),
        regimen=str(row.get("regimen", row.get("tipo_regimen", ""))),
        vigencia=vigencia,
        base_gravable=base,
        impuesto=impuesto,
        ingresos_exogena=exogena,
        tarifa_efectiva=safe_ratio(impuesto, base),
        ratio_exogena_declarado=safe_ratio(exogena, base),
    )


def build_benchmark(peers: list[ContributorMetrics], ciiu: str, regimen: str, vigencia: str) -> PeerBenchmark:
    bases = [p.base_gravable for p in peers if p.base_gravable > 0]
    tarifas = [p.tarifa_efectiva for p in peers if p.tarifa_efectiva is not None]
    ratios = [p.ratio_exogena_declarado for p in peers if p.ratio_exogena_declarado is not None]
    return PeerBenchmark(
        ciiu=ciiu,
        regimen=regimen,
        vigencia=vigencia,
        total_pares=len(peers),
        mediana_base_gravable=round(median(bases), 2),
        p10_base_gravable=round(percentile(bases, 10), 2),
        p25_base_gravable=round(percentile(bases, 25), 2),
        p75_base_gravable=round(percentile(bases, 75), 2),
        p90_base_gravable=round(percentile(bases, 90), 2),
        mediana_tarifa_efectiva=round(median(tarifas), 6),
        mediana_ratio_exogena_declarado=round(median(ratios), 4),
    )


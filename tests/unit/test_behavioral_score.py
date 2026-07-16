from domain.behavioral.behavioral_score import calcular_score_comportamental
from domain.behavioral.peer_group import ContributorMetrics, PeerBenchmark


def _make_contributor(contribuyente_nit="123", base=1000):
    return ContributorMetrics(
        contribuyente_nit=contribuyente_nit, razon_social="Test", ciiu="1234", regimen="GENERAL",
        vigencia="2024", base_gravable=base, impuesto=100,
        ingresos_exogena=1200, tarifa_efectiva=0.1, ratio_exogena_declarado=1.2,
    )


def test_score_bajo_p10():
    contrib = _make_contributor(base=50)
    peers = [_make_contributor(contribuyente_nit=str(i), base=1000 + i * 100) for i in range(20)]
    benchmark = PeerBenchmark(
        ciiu="1234", regimen="GENERAL", vigencia="2024", total_pares=20,
        mediana_base_gravable=2500, p10_base_gravable=1000, p25_base_gravable=1500,
        p75_base_gravable=3500, p90_base_gravable=4000,
        mediana_tarifa_efectiva=0.1, mediana_ratio_exogena_declarado=1.2,
    )
    result = calcular_score_comportamental(contrib, peers, benchmark, min_pares=10)
    assert result["score_comportamental"] > 30
    assert any(h["tipo"] == "BASE_GRAVABLE_BAJO_P10" for h in result["hallazgos"])


def test_score_bajo_p25():
    contrib = _make_contributor(base=1200)
    peers = [_make_contributor(contribuyente_nit=str(i), base=1000 + i * 100) for i in range(20)]
    benchmark = PeerBenchmark(
        ciiu="1234", regimen="GENERAL", vigencia="2024", total_pares=20,
        mediana_base_gravable=2500, p10_base_gravable=1000, p25_base_gravable=1500,
        p75_base_gravable=3500, p90_base_gravable=4000,
        mediana_tarifa_efectiva=0.1, mediana_ratio_exogena_declarado=1.2,
    )
    result = calcular_score_comportamental(contrib, peers, benchmark, min_pares=10)
    assert result["score_comportamental"] >= 15
    assert any(h["tipo"] == "BASE_GRAVABLE_BAJO_P25" for h in result["hallazgos"])


def test_score_bajo_muestra_pequena():
    contrib = _make_contributor(base=50)
    peers = [_make_contributor(contribuyente_nit=str(i), base=1000 + i * 100) for i in range(5)]
    benchmark = PeerBenchmark(
        ciiu="1234", regimen="GENERAL", vigencia="2024", total_pares=5,
        mediana_base_gravable=1500, p10_base_gravable=1000, p25_base_gravable=1200,
        p75_base_gravable=2000, p90_base_gravable=2500,
        mediana_tarifa_efectiva=0.1, mediana_ratio_exogena_declarado=1.2,
    )
    result = calcular_score_comportamental(contrib, peers, benchmark, min_pares=10)
    assert any(h["tipo"] == "MUESTRA_COMPARABLE_BAJA" for h in result["hallazgos"])

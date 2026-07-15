from domain.behavioral.seasonal import analizar_patrones_temporales


def test_caida_abrupta_detectada():
    historico = [
        {"periodo": "2023", "base_gravable": 1000000},
        {"periodo": "2024", "base_gravable": 100000},
    ]
    hallazgos = analizar_patrones_temporales(historico, "2025")
    assert any(h["tipo"] == "CAIDA_ABRUPTA_TEMPORAL" for h in hallazgos)


def test_tendencia_descendente():
    historico = [
        {"periodo": "2021", "base_gravable": 1000},
        {"periodo": "2022", "base_gravable": 800},
        {"periodo": "2023", "base_gravable": 600},
        {"periodo": "2024", "base_gravable": 400},
    ]
    hallazgos = analizar_patrones_temporales(historico, "2025")
    assert any(h["tipo"] == "TENDENCIA_DESCENDENTE" for h in hallazgos)


def test_desaparicion_detectada():
    historico = [
        {"periodo": "2022", "base_gravable": 500},
        {"periodo": "2023", "base_gravable": 600},
    ]
    hallazgos = analizar_patrones_temporales(historico, "2024")
    assert any(h["tipo"] == "DESAPARICION_DECLARATIVA" for h in hallazgos)


def test_historial_corto_sin_hallazgos():
    historico = [{"periodo": "2024", "base_gravable": 100}]
    hallazgos = analizar_patrones_temporales(historico, "2025")
    assert len(hallazgos) == 0

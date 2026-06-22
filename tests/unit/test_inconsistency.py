from domain.services.inconsistency_service import nivel_riesgo


def test_nivel_riesgo_alto():
    assert nivel_riesgo(85) == "ALTO"
    assert nivel_riesgo(70) == "ALTO"


def test_nivel_riesgo_medio():
    assert nivel_riesgo(55) == "MEDIO"
    assert nivel_riesgo(40) == "MEDIO"


def test_nivel_riesgo_bajo():
    assert nivel_riesgo(30) == "BAJO"
    assert nivel_riesgo(0) == "BAJO"

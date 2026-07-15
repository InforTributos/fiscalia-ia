from datetime import date

from domain.fiscalizacion.legal_window import calcular_ventana_legal, es_omiso
from domain.fiscalizacion.scoring import banda, calcular_score_hallazgo


def test_score_directa_alto():
    result = calcular_score_hallazgo("DIRECTA", 50000000, 100)
    assert result["score"] > 50
    assert result["banda"] in ("A", "B")


def test_score_indiciaria_bajo():
    result = calcular_score_hallazgo("INDICIARIA", 0, 1000)
    assert result["score"] < 40
    assert result["banda"] in ("C", "D")


def test_banda_a():
    assert banda(85) == "A"
    assert banda(65) == "B"
    assert banda(45) == "C"
    assert banda(20) == "D"


def test_ventana_legal():
    v = calcular_ventana_legal("2024")
    assert v.fecha_vencimiento_declaracion == date(2025, 4, 30)
    assert v.limite_firmeza == date(2028, 4, 30)
    assert v.limite_aforo == date(2030, 4, 30)


def test_es_omiso():
    assert es_omiso("OMISO") is True
    assert es_omiso("OMISO_INEXACTO") is True
    assert es_omiso("INEXACTO") is False

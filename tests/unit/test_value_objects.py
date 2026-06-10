import pytest
from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo
from domain.value_objects.score_riesgo import ScoreRiesgo
from domain.value_objects.dinero import Dinero


class TestNIT:
    def test_nit_vacio_lanza_error(self):
        with pytest.raises(ValueError, match="no puede estar vacío"):
            NIT("")

    def test_nit_solo_espacios_lanza_error(self):
        with pytest.raises(ValueError, match="no puede estar vacío"):
            NIT("   ")

    def test_nit_con_letras_lanza_error(self):
        with pytest.raises(ValueError, match="NIT inválido"):
            NIT("900ABC123")

    def test_nit_valido_sin_formato(self):
        nit = NIT("9003189639")
        assert nit.valor == "9003189639"

    def test_nit_valido_con_guiones(self):
        nit = NIT("900.318.963-9")
        assert nit.valor == "900.318.963-9"

    def test_nit_formateado(self):
        nit = NIT("  9003189639  ")
        assert nit.formateado() == "9003189639"


class TestPeriodo:
    def test_periodo_vacio_lanza_error(self):
        with pytest.raises(ValueError, match="Período inválido"):
            Periodo("")

    def test_periodo_muy_corto_lanza_error(self):
        with pytest.raises(ValueError, match="Período inválido"):
            Periodo("2025")

    def test_periodo_valido(self):
        p = Periodo("2025-01")
        assert p.valor == "2025-01"

    def test_periodo_year(self):
        p = Periodo("2025-01")
        assert p.year == "2025"

    def test_periodo_month(self):
        p = Periodo("2025-01")
        assert p.month == "01"

    def test_periodo_month_diciembre(self):
        p = Periodo("2024-12")
        assert p.year == "2024"
        assert p.month == "12"


class TestScoreRiesgo:
    def test_score_negativo_lanza_error(self):
        with pytest.raises(ValueError, match="Score debe estar entre 0 y 100"):
            ScoreRiesgo(-1)

    def test_score_mayor_100_lanza_error(self):
        with pytest.raises(ValueError, match="Score debe estar entre 0 y 100"):
            ScoreRiesgo(101)

    def test_score_cero(self):
        s = ScoreRiesgo(0)
        assert s.valor == 0
        assert s.nivel == "BAJO"

    def test_score_100(self):
        s = ScoreRiesgo(100)
        assert s.valor == 100
        assert s.nivel == "ALTO"

    def test_score_alto(self):
        s = ScoreRiesgo(85)
        assert s.nivel == "ALTO"

    def test_score_alto_limite_inferior(self):
        s = ScoreRiesgo(70)
        assert s.nivel == "ALTO"

    def test_score_medio(self):
        s = ScoreRiesgo(55)
        assert s.nivel == "MEDIO"

    def test_score_medio_limite_inferior(self):
        s = ScoreRiesgo(40)
        assert s.nivel == "MEDIO"

    def test_score_bajo(self):
        s = ScoreRiesgo(20)
        assert s.nivel == "BAJO"

    def test_score_bajo_limite_superior(self):
        s = ScoreRiesgo(39)
        assert s.nivel == "BAJO"


class TestDinero:
    def test_monto_negativo_lanza_error(self):
        with pytest.raises(ValueError, match="Monto no puede ser negativo"):
            Dinero(-100)

    def test_monto_cero(self):
        d = Dinero(0)
        assert d.valor == 0

    def test_monto_valido(self):
        d = Dinero(1_000_000)
        assert d.valor == 1_000_000

    def test_suma(self):
        a = Dinero(500_000)
        b = Dinero(300_000)
        r = a + b
        assert r.valor == 800_000

    def test_resta(self):
        a = Dinero(500_000)
        b = Dinero(200_000)
        r = a - b
        assert r.valor == 300_000

    def test_repr(self):
        d = Dinero(1_500_000)
        assert "$1,500,000" in repr(d)

    def test_repr_cero(self):
        d = Dinero(0)
        assert "$0" in repr(d)

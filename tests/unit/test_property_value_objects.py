from domain.value_objects.dinero import Dinero
from domain.value_objects.nit import NIT
from domain.value_objects.score_riesgo import ScoreRiesgo
from hypothesis import given
from hypothesis import strategies as st


class TestNITProperty:
    @given(st.text(min_size=1))
    def test_nit_siempre_tiene_valor(self, valor):
        try:
            nit = NIT(valor)
            assert nit.valor is not None
            assert isinstance(nit.formateado(), str)
        except ValueError:
            pass

    @given(st.from_regex(r"\d{8,10}", fullmatch=True))
    def test_nit_solo_digitos_es_valido(self, digitos):
        nit = NIT(digitos)
        assert nit.formateado() == digitos


class TestScoreRiesgoProperty:
    @given(st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False))
    def test_score_siempre_entre_cero_y_cien(self, valor):
        score = ScoreRiesgo(valor)
        assert 0 <= score.valor <= 100
        assert score.nivel in ("ALTO", "MEDIO", "BAJO")

    @given(st.floats(min_value=0, max_value=39, allow_nan=False, allow_infinity=False))
    def test_score_bajo(self, valor):
        score = ScoreRiesgo(valor)
        assert score.nivel == "BAJO"

    @given(st.floats(min_value=40, max_value=69, allow_nan=False, allow_infinity=False))
    def test_score_medio(self, valor):
        score = ScoreRiesgo(valor)
        assert score.nivel == "MEDIO"

    @given(st.floats(min_value=70, max_value=100, allow_nan=False, allow_infinity=False))
    def test_score_alto(self, valor):
        score = ScoreRiesgo(valor)
        assert score.nivel == "ALTO"


class TestDineroProperty:
    @given(st.floats(min_value=0, max_value=1e12, allow_nan=False, allow_infinity=False))
    def test_dinero_no_negativo(self, valor):
        dinero = Dinero(valor)
        assert dinero.valor >= 0

    @given(
        st.floats(min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False),
    )
    def test_suma_commutativa(self, a, b):
        d1 = Dinero(a) + Dinero(b)
        d2 = Dinero(b) + Dinero(a)
        assert abs(d1.valor - d2.valor) < 0.01

    @given(st.floats(min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False))
    def test_resta_no_mayor_que_original(self, valor):
        dinero = Dinero(valor)
        try:
            resultado = dinero - Dinero(valor / 2)
            assert resultado.valor <= dinero.valor
        except ValueError:
            pass

from api.schemas.analisis import AnalisisResponse, HallazgoDTO
from api.schemas.contribuyente import Contribuyente
from api.schemas.score import ComponenteSRFDTO, ScoreResponse


class TestSchemas:
    def test_hallazgo_dto_minimal(self):
        h = HallazgoDTO(tipo="SUBREGISTRO", severidad="ALTA", descripcion="test")
        assert h.tipo == "SUBREGISTRO"
        assert h.diferencia is None

    def test_hallazgo_dto_full(self):
        h = HallazgoDTO(tipo="SUBREGISTRO", severidad="ALTA", descripcion="test", diferencia=70_000_000, ciiu="4711")
        assert h.diferencia == 70_000_000
        assert h.ciiu == "4711"

    def test_analisis_response(self):
        r = AnalisisResponse(
            nit="9003189639",
            periodo="2025-01",
            score_riesgo=85.0,
            nivel_riesgo="ALTO",
            hallazgos=[],
            explicacion_srf="test",
            tiempo_analisis_ms=100,
        )
        assert r.nit == "9003189639"
        assert r.cache_hit is False
        assert r.modo_degradado is False

    def test_contribuyente_minimal(self):
        c = Contribuyente(nit="9003189639")
        assert c.nit == "9003189639"
        assert c.razon_social is None

    def test_contribuyente_full(self):
        c = Contribuyente(nit="9003189639", razon_social="Test SAS", ciiu="4711")
        assert c.razon_social == "Test SAS"

    def test_componente_srf(self):
        comp = ComponenteSRFDTO(nombre="Exógena", valor=35.0, peso=0.4)
        assert comp.nombre == "Exógena"

    def test_score_response(self):
        r = ScoreResponse(
            nit="9003189639", srf=85.0, nivel="ALTO", componentes=[], explicacion_ia="test", tiempo_analisis_ms=100
        )
        assert r.srf == 85.0
        assert r.nivel == "ALTO"

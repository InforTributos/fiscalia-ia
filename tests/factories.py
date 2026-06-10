import factory
from domain.entities.contribuyente import Contribuyente
from domain.entities.hallazgo import Hallazgo
from domain.value_objects.dinero import Dinero
from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo
from domain.value_objects.score_riesgo import ScoreRiesgo
from faker import Faker

fake = Faker("es-CO")


class NITFactory(factory.Factory):
    class Meta:
        model = NIT

    valor = factory.LazyFunction(lambda: fake.numerify("9########"))


class PeriodoFactory(factory.Factory):
    class Meta:
        model = Periodo

    valor = factory.LazyFunction(lambda: f"{fake.year()}-{fake.month():02d}")


class ScoreRiesgoFactory(factory.Factory):
    class Meta:
        model = ScoreRiesgo

    valor = factory.Faker("pyfloat", min_value=0, max_value=100)


class DineroFactory(factory.Factory):
    class Meta:
        model = Dinero

    valor = factory.Faker("pyfloat", min_value=0, max_value=500_000_000)


class HallazgoFactory(factory.Factory):
    class Meta:
        model = Hallazgo

    tipo = factory.Iterator(["SUBREGISTRO", "SOBREREGISTRO", "OMISION", "INCONSISTENCIA"])
    severidad = factory.Iterator(["ALTA", "MEDIA", "BAJA"])
    descripcion = factory.Faker("sentence", nb_words=12, locale="es_CO")
    diferencia = factory.SubFactory(DineroFactory)
    declarado = factory.SubFactory(DineroFactory)
    referencia = factory.SubFactory(DineroFactory)
    ciiu = factory.Iterator(["4711", "5611", "6820", "8511"])
    explicacion_ia = None
    recomendacion = None


class ContribuyenteFactory(factory.Factory):
    class Meta:
        model = Contribuyente

    nit = factory.SubFactory(NITFactory)
    razon_social = factory.Faker("company", locale="es_CO")
    ciiu = factory.Iterator(["4711", "5611", "6820", "8511", "6201"])
    municipio = factory.Iterator(["VALLEDUPAR", "AGUACHICA", "BOSCONIA", "CODazzi"])
    estado = factory.Iterator(["ACTIVO", "SUSPENDIDO", "INACTIVO"])
    direccion = factory.Faker("address", locale="es_CO")


def hacer_cruce(**kwargs) -> dict:
    """Construye un dict de cruce con valores por defecto."""
    data = {
        "ciiu": "4711",
        "ingreso_declarado": 50_000_000,
        "ingreso_exogena": 120_000_000,
        "diferencia": 70_000_000,
        "variacion_pct": 140,
        "umbral_superado": 1,
    }
    data.update(kwargs)
    return data


def hacer_inconsistencia(**kwargs) -> dict:
    """Construye un dict de inconsistencia con valores por defecto."""
    data = {
        "tipo_incidencia": "SUBREGISTRO",
        "ciiu": "4711",
        "descripcion": "Subdeclaración detectada",
        "valor_declarado": 50_000_000,
        "valor_referencia": 120_000_000,
        "diferencia": 70_000_000,
        "severidad": "ALTA",
    }
    data.update(kwargs)
    return data


def hacer_srf(**kwargs) -> dict:
    """Construye un dict de SRF con valores por defecto."""
    data = {
        "srf_total": 85,
        "comp_exogena": 35,
        "comp_tarifa": 25,
        "comp_omision": 20,
        "comp_rues": 5,
    }
    data.update(kwargs)
    return data

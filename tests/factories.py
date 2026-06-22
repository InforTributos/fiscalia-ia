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


def hacer_datos_mcp(**kwargs) -> dict:
    data = {
        "nit": "9003189639",
        "score_peso": 75.5,
        "es_candidato": True,
        "razon": "Diferencia de ingresos del 45%",
        "razon_social": "COMERCIO XYZ S.A.S.",
        "ciiu": "4711",
        "pagina": 1,
    }
    data.update(kwargs)
    return data


def hacer_datos_fiscales(**kwargs) -> dict:
    data = {
        "nit": "9003189639",
        "razon_social": "COMERCIO XYZ S.A.S.",
        "ciiu": "4711",
        "regimen": "COMUN",
        "declaraciones_ica": [
            {"periodo": "2024-B1", "base_gravable": 50000000, "tarifa": 0.01, "impuesto": 500000},
        ],
        "exogena_dian": [
            {"periodo": "2024", "ingresos": 120000000},
        ],
        "rues_estado": "ACTIVO",
        "rues_fecha_constitucion": "2015-03-15",
    }
    data.update(kwargs)
    return data


def hacer_inconsistencia(**kwargs) -> dict:
    data = {
        "tipo_incidencia": "SUBREGISTRO",
        "ciiu": "4711",
        "descripcion": "Subdeclaración detectada",
        "valor_declarado": 50000000,
        "valor_referencia": 120000000,
        "diferencia": 70000000,
        "severidad": "ALTA",
    }
    data.update(kwargs)
    return data

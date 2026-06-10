import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "microservice"))


@pytest.fixture
def contexto_analisis_completo():
    return {
        "tipo": "analisis_completo",
        "nit": "9003189639",
        "periodo": "2025-01",
        "cruces": [
            {
                "ciiu": "4711",
                "ingreso_declarado": 50_000_000,
                "ingreso_exogena": 120_000_000,
                "diferencia": 70_000_000,
                "variacion_pct": 140,
                "umbral_superado": 1,
            }
        ],
        "inconsistencias": [
            {
                "tipo_incidencia": "SUBREGISTRO",
                "ciiu": "4711",
                "descripcion": "Subdeclaración detectada: exógena reporta 120M vs 50M declarados",
                "valor_declarado": 50_000_000,
                "valor_referencia": 120_000_000,
                "diferencia": 70_000_000,
                "severidad": "ALTA",
            }
        ],
        "srf": {
            "srf_total": 85,
            "comp_exogena": 35,
            "comp_tarifa": 25,
            "comp_omision": 20,
            "comp_rues": 5,
        },
    }


@pytest.fixture
def contexto_explicacion_srf():
    return {
        "tipo": "explicacion_srf",
        "nit": "9003189639",
        "periodo": "2025-01",
        "srf": {
            "srf_total": 45,
            "comp_exogena": 15,
            "comp_tarifa": 10,
            "comp_omision": 12,
            "comp_rues": 8,
        },
    }

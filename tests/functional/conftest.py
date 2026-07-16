import uuid

import httpx
import pytest

API_BASE = "http://localhost:8000/api/v1"

SEED_NITS = [
    "1065819988", "901501675", "901473230", "1065632021",
    "77195663", "1065858508", "1067810559", "15174506",
    "22581507", "900818892", "1051659301", "22587368",
]


@pytest.fixture(scope="session")
def api_base() -> str:
    return API_BASE


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE, timeout=60.0)


@pytest.fixture(scope="session")
def seed_nits() -> list[str]:
    return SEED_NITS


@pytest.fixture(scope="session")
def valid_nit(seed_nits) -> str:
    return seed_nits[0]


@pytest.fixture(scope="session")
def proceso_payload() -> dict:
    return {
        "entidad_nit": "800098911-8",
        "nombre": f"Test Proceso {uuid.uuid4().hex[:8]}",
        "vigencia_ini": "2024-01-01",
        "vigencia_fin": "2024-12-31",
        "tipo_regimen": "COMUN",
        "actividades_economicas": ["4711", "4712"],
        "periodo": "2024",
    }


@pytest.fixture(scope="session")
def campana_payload() -> dict:
    return {
        "periodo": "2024",
        "nombre": f"Campana test {uuid.uuid4().hex[:8]}",
        "umbral_retenciones_pct": 5.0,
    }


@pytest.fixture(scope="session")
def hallazgo_payload(valid_nit) -> dict:
    return {
        "contribuyente_nit": valid_nit,
        "regla": "SUBDECLARACION",
        "periodo": "2024",
        "tipo_hallazgo": "SUBDECLARACION_ICA",
        "fuerza_probatoria": "MEDIA",
        "brecha_valor": 50000000.0,
        "impuesto_estimado": 7500000.0,
        "resumen": "Diferencia detectada entre ingresos declarados y exogena",
        "evidencias": [
            {
                "fuente": "EXOGENA_DIAN",
                "descripcion": "Diferencia del 45% en ingresos reportados",
                "snapshot": {"declarado": 100000000, "exogena": 150000000},
            }
        ],
    }


@pytest.fixture(scope="session")
def fiscalizacion_payload(valid_nit) -> dict:
    return {
        "contribuyente_nit": valid_nit,
        "periodo": "2024",
        "reglas": ["SUBDECLARACION", "OMISION_TOTAL"],
        "declaraciones_ica": [
            {"id": 1, "base_gravable": 100000000, "impuesto": 5000000, "periodo": "01-2024"}
        ],
        "exogena_dian": [
            {"ingresos": 150000000, "periodo": "2024"}
        ],
    }


@pytest.fixture(scope="session")
def revision_payload() -> dict:
    return {
        "funcionario_id": "test-func-001",
        "decision": "CONFIRMAR",
        "motivo": "Prueba funcional de revision",
    }

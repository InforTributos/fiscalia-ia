from unittest.mock import AsyncMock

import pytest
from domain.ports.lookup_repository import AtributosICA, ConfiguracionDeclaracion, LookupRepository
from infrastructure.mcp.pagination import (
    PAGINAR_CONTRIBUYENTES_SQL,
    obtener_datos_fiscales,
    obtener_inexactos_ciiu,
    obtener_inexactos_retenciones,
    obtener_omisos_conocidos,
    obtener_omisos_desconocidos,
    paginar_contribuyentes,
)


@pytest.fixture
def mock_lookup():
    repo = AsyncMock(spec=LookupRepository)
    repo.get_impuesto_id.return_value = 102
    repo.get_programa_id.return_value = 2
    repo.get_configuracion_declaracion.return_value = ConfiguracionDeclaracion(
        ind_prsntcion_dclrcion="A",
        cdgo_clnte=10,
    )
    repo.get_atributos_ica.return_value = AtributosICA(
        ciiu_ids=[5125],
        tarifa_ids=[2107],
        ret_recibidas_ids=[2135],
        ret_practicadas_ids=[2136],
    )
    return repo


@pytest.mark.asyncio
async def test_obtener_datos_fiscales_retorna_dict_completo():
    client = AsyncMock()
    client.execute_sql.side_effect = [
        [{"nit": "9003189639", "razon_social": "TEST S.A.S.",
          "ciiu": "4711", "regimen": "A", "id_sjto_impsto": 12345}],
        [{"periodo": "2024", "base_gravable": 50000000, "impuesto": 400000, "vlor_pago": 400000}],
        [{"periodo": "2024", "ingresos": 120000000}],
    ]

    result = await obtener_datos_fiscales(client, "9003189639", "2024")

    assert result is not None
    assert result["nit"] == "9003189639"
    assert result["razon_social"] == "TEST S.A.S."
    assert result["ciiu"] == "4711"
    assert result["regimen"] == "A"
    assert result["rues_estado"] == ""
    assert len(result["declaraciones_ica"]) == 1
    assert result["declaraciones_ica"][0]["base_gravable"] == 50000000
    assert len(result["exogena_dian"]) == 1
    assert result["exogena_dian"][0]["ingresos"] == 120000000
    assert client.execute_sql.call_count == 3


@pytest.mark.asyncio
async def test_obtener_datos_fiscales_sin_contribuyente_retorna_none():
    client = AsyncMock()
    client.execute_sql.return_value = None

    result = await obtener_datos_fiscales(client, "9999999999", "2024")
    assert result is None


@pytest.mark.asyncio
async def test_obtener_datos_fiscales_contribuyente_dict_sin_lista():
    client = AsyncMock()
    client.execute_sql.side_effect = [
        {"nit": "123", "razon_social": "SINGLE S.A.", "ciiu": "4711",
         "regimen": "COMUN", "rues_estado": "ACTIVO"},
        [],
        [],
    ]

    result = await obtener_datos_fiscales(client, "123", "2024")
    assert result is not None
    assert result["nit"] == "123"
    assert result["razon_social"] == "SINGLE S.A."


@pytest.mark.asyncio
async def test_obtener_datos_fiscales_sin_declaraciones():
    client = AsyncMock()
    client.execute_sql.side_effect = [
        [{"nit": "123", "razon_social": "TEST", "ciiu": "4711",
          "regimen": "COMUN", "rues_estado": "ACTIVO"}],
        None,
        None,
    ]

    result = await obtener_datos_fiscales(client, "123", "2024")
    assert result["declaraciones_ica"] == []
    assert result["exogena_dian"] == []


@pytest.mark.asyncio
async def test_paginar_contribuyentes_sql_placeholders():
    client = AsyncMock()
    client.execute_sql.return_value = []

    items = []
    async for item in paginar_contribuyentes(
        client,
        vigencia_ini="2023-01-01",
        vigencia_fin="2023-12-31",
        tipo_regimen="COMUN",
        actividades_economicas=["4711", "4721"],
        periodo="2023",
    ):
        items.append(item)

    assert len(items) == 0
    call_args = client.execute_sql.call_args_list[0]
    sql = call_args.args[0]
    bind = call_args.args[1]
    assert sql == PAGINAR_CONTRIBUYENTES_SQL.format(actividades_placeholders=":a0, :a1")
    assert bind["a0"] == "4711"
    assert bind["a1"] == "4721"
    assert bind["tipo_regimen"] == "COMUN"
    assert bind["offset"] == 0
    assert bind["limit"] == 100


@pytest.mark.asyncio
async def test_paginar_contribuyentes_paginacion_completa():
    client = AsyncMock()
    page_size = 3
    client.execute_sql.side_effect = [
        [{"nit": "1"}, {"nit": "2"}, {"nit": "3"}],
        [{"nit": "4"}, {"nit": "5"}, {"nit": "6"}],
        [{"nit": "7"}, {"nit": "8"}],
    ]

    items = []
    async for item in paginar_contribuyentes(
        client,
        vigencia_ini="2024-01-01",
        vigencia_fin="2024-12-31",
        tipo_regimen="COMUN",
        actividades_economicas=["4711"],
        periodo="2024",
        page_size=page_size,
    ):
        items.append(item)

    assert len(items) == 8
    assert items[0]["nit"] == "1"
    assert items[7]["nit"] == "8"
    assert client.execute_sql.call_count == 3

    offsets = [c.args[1]["offset"] for c in client.execute_sql.call_args_list]
    assert offsets == [0, 3, 6]
    limits = [c.args[1]["limit"] for c in client.execute_sql.call_args_list]
    assert limits == [3, 3, 3]


@pytest.mark.asyncio
async def test_paginar_contribuyentes_resultado_vacio_termina():
    client = AsyncMock()
    client.execute_sql.return_value = []

    items = []
    async for item in paginar_contribuyentes(
        client,
        vigencia_ini="2024-01-01",
        vigencia_fin="2024-12-31",
        tipo_regimen="SIMPLIFICADO",
        actividades_economicas=["9999"],
        periodo="2024",
    ):
        items.append(item)

    assert len(items) == 0
    assert client.execute_sql.call_count == 1


@pytest.mark.asyncio
async def test_omisos_conocidos_usa_tablas_reales(mock_lookup):
    client = AsyncMock()
    client.execute_sql.return_value = [
        {"idntfccion": "9003189639", "nmbre_rzon_scial": "TEST S.A.",
         "id_actvdad_ecnmca": "4711", "drccion": "Calle 10", "id_sjto_impsto": 123},
    ]

    items = await _collect(obtener_omisos_conocidos(client, mock_lookup, "2024", "2024", 50))
    assert len(items) == 1
    assert items[0]["idntfccion"] == "9003189639"


@pytest.mark.asyncio
async def test_omisos_desconocidos_dian_sin_registro(mock_lookup):
    client = AsyncMock()
    repo = mock_lookup
    repo.get_programa_id.return_value = 1
    client.execute_sql.return_value = [
        {"nit": "9012345678", "razon_social": "NO REGISTRADA S.A.",
         "ciiu": "4721", "valor_dian": 50000000, "vgncia": "2024"},
    ]

    items = await _collect(obtener_omisos_desconocidos(client, repo, "2024", 50))
    assert len(items) == 1
    assert items[0]["nit"] == "9012345678"


@pytest.mark.asyncio
async def test_inexactos_ciiu_tarifa_dian_mayor(mock_lookup):
    client = AsyncMock()
    client.execute_sql.return_value = [
        {"idntfccion": "9003189639", "nmbre_rzon_scial": "TEST",
         "ciiu_declarado": "4711", "tarifa_declarada": 0.008,
         "ciiu_dian": "4721", "tarifa_dian": 0.010},
    ]

    items = await _collect(obtener_inexactos_ciiu(client, mock_lookup, "2024", 50))
    assert len(items) == 1
    assert items[0]["ciiu_declarado"] == "4711"


@pytest.mark.asyncio
async def test_inexactos_retenciones_diferencia_mayor_umbral(mock_lookup):
    client = AsyncMock()
    client.execute_sql.return_value = [
        {"idntfccion": "9003189639", "nmbre_rzon_scial": "TEST",
         "retenciones_declaradas_practicadas": 500000,
         "retenciones_exogena_practicadas": 750000,
         "diferencia_pct": 33.3},
    ]

    items = await _collect(obtener_inexactos_retenciones(client, mock_lookup, "2024", 50))
    assert len(items) == 1
    assert items[0]["diferencia_pct"] == 33.3


async def _collect(agen):
    items = []
    async for item in agen:
        items.append(item)
    return items

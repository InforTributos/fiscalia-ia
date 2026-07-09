from unittest.mock import AsyncMock

import pytest
from infrastructure.persistence.repositorio_lookup import RepositorioLookupOracle


@pytest.mark.asyncio
async def test_get_impuesto_id_resuelve_por_codigo():
    client = AsyncMock()
    client.execute_sql.return_value = [{"id_impsto": 102}]
    repo = RepositorioLookupOracle(client)

    result = await repo.get_impuesto_id("ICA")

    assert result == 102
    client.execute_sql.assert_called_once_with(
        "SELECT id_impsto FROM DF_C_IMPUESTOS WHERE cdgo_impsto = :cdgo",
        {"cdgo": "ICA"},
    )


@pytest.mark.asyncio
async def test_get_impuesto_id_cachea_resultado():
    client = AsyncMock()
    client.execute_sql.return_value = [{"id_impsto": 102}]
    repo = RepositorioLookupOracle(client)

    await repo.get_impuesto_id("ICA")
    await repo.get_impuesto_id("ICA")

    assert client.execute_sql.call_count == 1


@pytest.mark.asyncio
async def test_get_impuesto_id_lanza_error_si_no_existe():
    client = AsyncMock()
    client.execute_sql.return_value = None
    repo = RepositorioLookupOracle(client)

    with pytest.raises(ValueError, match="'XYZ' no encontrado"):
        await repo.get_impuesto_id("XYZ")


@pytest.mark.asyncio
async def test_get_programa_id_resuelve_por_codigo():
    client = AsyncMock()
    client.execute_sql.return_value = [{"id_prgrma": 2}]
    repo = RepositorioLookupOracle(client)

    result = await repo.get_programa_id("O")

    assert result == 2
    client.execute_sql.assert_called_once_with(
        "SELECT id_prgrma FROM FI_D_PROGRAMAS WHERE cdgo_prgrma = :cdgo",
        {"cdgo": "O"},
    )


@pytest.mark.asyncio
async def test_get_programa_id_cachea():
    client = AsyncMock()
    client.execute_sql.side_effect = [
        [{"id_prgrma": 1}],
        [{"id_prgrma": 2}],
    ]
    repo = RepositorioLookupOracle(client)

    assert await repo.get_programa_id("OD") == 1
    assert await repo.get_programa_id("O") == 2
    assert await repo.get_programa_id("OD") == 1

    assert client.execute_sql.call_count == 2


@pytest.mark.asyncio
async def test_get_atributos_ica_resuelve_ids():
    client = AsyncMock()
    client.execute_sql.side_effect = [
        [{"id_impsto": 102}],
        [{"id_frmlrio": 284, "cdgo_frmlrio": "FIB-V2020"}],
        [
            {"id_frmlrio_rgion_atrbto": 1962, "nmbre_dsplay": "CODIGO CIIU", "cdgo_atrbto_tpo": "SLQ", "region_dscrpcion": "B. DETERMINACION DE LA BASE GRAVABLE"},
            {"id_frmlrio_rgion_atrbto": 1963, "nmbre_dsplay": "TARIFA ACTIVIDAD ECONOMICA", "cdgo_atrbto_tpo": "NUM", "region_dscrpcion": "B. DETERMINACION DE LA BASE GRAVABLE"},
            {"id_frmlrio_rgion_atrbto": 1996, "nmbre_dsplay": "RETENCIONES DE INDUSTRIA Y COMERCIO QUE LE PRACTICARON EN EL PERIODO", "cdgo_atrbto_tpo": "NUM", "region_dscrpcion": "D. LIQUIDACION PRIVADA"},
            {"id_frmlrio_rgion_atrbto": 1997, "nmbre_dsplay": "AUTORRETENCIONES DEL IMPUESTO DE INDUSTRIA Y COMERCIO PRACTICADAS EN EL PERIODO", "cdgo_atrbto_tpo": "NUM", "region_dscrpcion": "D. LIQUIDACION PRIVADA"},
        ],
    ]
    repo = RepositorioLookupOracle(client)

    result = await repo.get_atributos_ica("2024")

    assert result.ciiu_ids == [1962]
    assert result.tarifa_ids == [1963]
    assert result.ret_recibidas_ids == [1996]
    assert result.ret_practicadas_ids == [1997]


@pytest.mark.asyncio
async def test_get_atributos_ica_cachea():
    client = AsyncMock()
    client.execute_sql.side_effect = [
        [{"id_impsto": 102}],
        [{"id_frmlrio": 284, "cdgo_frmlrio": "FIB-V2020"}],
        [{"id_frmlrio_rgion_atrbto": 1962, "nmbre_dsplay": "CODIGO CIIU", "cdgo_atrbto_tpo": "SLQ", "region_dscrpcion": "B"}],
    ]
    repo = RepositorioLookupOracle(client)

    await repo.get_atributos_ica("2024")
    await repo.get_atributos_ica("2024")

    assert client.execute_sql.call_count == 3


@pytest.mark.asyncio
async def test_get_atributos_ica_sin_atributos_lanza_error():
    client = AsyncMock()
    client.execute_sql.side_effect = [
        [{"id_impsto": 102}],
        [{"id_frmlrio": 284, "cdgo_frmlrio": "FUN - V2020"}],
        [],
    ]
    repo = RepositorioLookupOracle(client)

    with pytest.raises(ValueError, match="atributos para formularios ICA"):
        await repo.get_atributos_ica("2024")


@pytest.mark.asyncio
async def test_get_atributos_ica_sin_formularios_lanza_error():
    client = AsyncMock()
    client.execute_sql.side_effect = [
        [{"id_impsto": 102}],
        [],
    ]
    repo = RepositorioLookupOracle(client)

    with pytest.raises(ValueError, match="No se encontraron formularios"):
        await repo.get_atributos_ica("2024")


@pytest.mark.asyncio
async def test_get_programas_por_impuesto_filtra_por_codigos():
    client = AsyncMock()
    client.execute_sql.return_value = [
        {"id_prgrma": 2, "cdgo_prgrma": "O", "nmbre_prgrma": "OMISOS"},
        {"id_prgrma": 22, "cdgo_prgrma": "I", "nmbre_prgrma": "INEXACTOS"},
    ]
    repo = RepositorioLookupOracle(client)

    result = await repo.get_programas_por_impuesto(102, cdgos_prgrma=["O", "I"])

    assert len(result) == 2
    assert result[0].id_prgrma == 2
    assert result[1].cdgo_prgrma == "I"


@pytest.mark.asyncio
async def test_get_configuracion_declaracion_retorna_config():
    client = AsyncMock()
    client.execute_sql.return_value = [
        {"cdgo_clnte": 10, "ind_prsntcion_dclrcion": "A"},
    ]
    repo = RepositorioLookupOracle(client)

    result = await repo.get_configuracion_declaracion()

    assert result.cdgo_clnte == 10
    assert result.ind_prsntcion_dclrcion == "A"


@pytest.mark.asyncio
async def test_get_configuracion_declaracion_cachea():
    client = AsyncMock()
    client.execute_sql.return_value = [
        {"cdgo_clnte": 10, "ind_prsntcion_dclrcion": "A"},
    ]
    repo = RepositorioLookupOracle(client)

    await repo.get_configuracion_declaracion()
    await repo.get_configuracion_declaracion()

    assert client.execute_sql.call_count == 1


@pytest.mark.asyncio
async def test_get_atributos_ica_filtra_por_tipo_formulario():
    client = AsyncMock()
    client.execute_sql.side_effect = [
        [{"id_impsto": 102}],
        [{"id_frmlrio": 305, "cdgo_frmlrio": "FUN - V2020"}],
        [
            {"id_frmlrio_rgion_atrbto": 5125, "nmbre_dsplay": "CODIGO CIIU", "cdgo_atrbto_tpo": "SLQ", "region_dscrpcion": "C. DISCRIMINACIÓN DE ACTIVIDADES GRAVADAS"},
            {"id_frmlrio_rgion_atrbto": 2107, "nmbre_dsplay": "TARIFA ( por mil )", "cdgo_atrbto_tpo": "TXT", "region_dscrpcion": "C. DISCRIMINACIÓN DE ACTIVIDADES GRAVADAS"},
            {"id_frmlrio_rgion_atrbto": 2135, "nmbre_dsplay": "26. MENOS RETENCIONES que le practicaron a favor de este municipio o distrito en este periodo", "cdgo_atrbto_tpo": "TXT", "region_dscrpcion": "D. LIQUIDACIÓN PRIVADA"},
            {"id_frmlrio_rgion_atrbto": 2136, "nmbre_dsplay": "27. MENOS AUTORRETENCIONES practicadas a favor de este municipio o distrito en este periodo", "cdgo_atrbto_tpo": "TXT", "region_dscrpcion": "D. LIQUIDACIÓN PRIVADA"},
        ],
    ]
    repo = RepositorioLookupOracle(client)

    result = await repo.get_atributos_ica("2024", tipo_formulario="FUN")

    assert result.ciiu_ids == [5125]
    assert result.tarifa_ids == [2107]
    assert result.ret_recibidas_ids == [2135]
    assert result.ret_practicadas_ids == [2136]

    form_call = client.execute_sql.call_args_list[1]
    assert "LIKE" in form_call.args[0]
    assert form_call.args[1].get("tipo_pattern") == "FUN%"


@pytest.mark.asyncio
async def test_get_atributos_ica_cachea_por_tipo():
    client = AsyncMock()
    client.execute_sql.side_effect = [
        [{"id_impsto": 102}],
        [{"id_frmlrio": 305, "cdgo_frmlrio": "FUN - V2020"}],
        [{"id_frmlrio_rgion_atrbto": 5125, "nmbre_dsplay": "CODIGO CIIU", "cdgo_atrbto_tpo": "SLQ", "region_dscrpcion": "C"}],
    ]
    repo = RepositorioLookupOracle(client)

    await repo.get_atributos_ica("2024", "FUN")
    await repo.get_atributos_ica("2024", "FUN")

    assert client.execute_sql.call_count == 3

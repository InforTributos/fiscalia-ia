from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from infrastructure.mcp.behavioral import OracleBehavioralRepository


@pytest.mark.asyncio
@patch("infrastructure.mcp.behavioral.OracleClient")
async def test_obtener_contribuyente_found(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.execute_sql = AsyncMock()
    mock_client.execute_sql.return_value = [
        {"nit": "123", "razon_social": "Test SA", "ciiu": "4711", "regimen": "COMUN",
         "base_gravable": 1000.0, "impuesto": 50.0, "ingresos_exogena": 5000.0},
    ]

    repo = OracleBehavioralRepository()
    result = await repo.obtener_contribuyente("123", "2024")

    assert result is not None
    assert result["nit"] == "123"
    assert result["razon_social"] == "Test SA"
    assert result["base_gravable"] == 1000.0
    mock_client.execute_sql.assert_awaited_once_with(
        mock_client.execute_sql.await_args_list[0][0][0],
        {"nit": "123", "periodo": "2024"},
    )


@pytest.mark.asyncio
@patch("infrastructure.mcp.behavioral.OracleClient")
async def test_obtener_contribuyente_not_found(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.execute_sql = AsyncMock()
    mock_client.execute_sql.return_value = []

    repo = OracleBehavioralRepository()
    result = await repo.obtener_contribuyente("999", "2024")

    assert result is None


@pytest.mark.asyncio
@patch("infrastructure.mcp.behavioral.OracleClient")
async def test_obtener_historico_nit_with_data(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.execute_sql = AsyncMock()
    mock_client.execute_sql.return_value = [
        {"periodo": 2022, "base_gravable": 500.0, "impuesto": 25.0, "ingresos_exogena": 3000.0},
        {"periodo": 2023, "base_gravable": 800.0, "impuesto": 40.0, "ingresos_exogena": 4500.0},
    ]

    repo = OracleBehavioralRepository()
    result = await repo.obtener_historico_nit("123")

    assert len(result) == 2
    assert result[0]["periodo"] == 2022
    assert result[1]["periodo"] == 2023
    assert result[0]["base_gravable"] == 500.0


@pytest.mark.asyncio
@patch("infrastructure.mcp.behavioral.OracleClient")
async def test_obtener_historico_nit_empty(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.execute_sql = AsyncMock()
    mock_client.execute_sql.return_value = []

    repo = OracleBehavioralRepository()
    result = await repo.obtener_historico_nit("999")

    assert result == []


@pytest.mark.asyncio
@patch("infrastructure.mcp.behavioral.OracleClient")
async def test_obtener_historico_nit_single_row(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.execute_sql = AsyncMock()
    mock_client.execute_sql.return_value = [
        {"periodo": 2024, "base_gravable": 100.0, "impuesto": 5.0, "ingresos_exogena": 500.0},
    ]

    repo = OracleBehavioralRepository()
    result = await repo.obtener_historico_nit("123")

    assert len(result) == 1
    assert result[0]["periodo"] == 2024


@pytest.mark.asyncio
@patch("infrastructure.mcp.behavioral.OracleClient")
async def test_obtener_pares_happy_path(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.execute_sql = AsyncMock()
    page_1 = [{"nit": str(i), "razon_social": f"Test {i}"} for i in range(500)]
    page_2 = [{"nit": "600", "razon_social": "Test 600"}]
    mock_client.execute_sql.side_effect = [page_1, page_2]

    repo = OracleBehavioralRepository()
    result = await repo.obtener_pares("2024", "4711", "COMUN")

    assert len(result) == 501
    assert mock_client.execute_sql.await_count == 2


@pytest.mark.asyncio
@patch("infrastructure.mcp.behavioral.OracleClient")
async def test_obtener_pares_multiple_pages(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.execute_sql = AsyncMock()
    page = [{"nit": str(i), "razon_social": f"Test {i}"} for i in range(500)]
    mock_client.execute_sql.side_effect = [page, page, page[:200]]

    repo = OracleBehavioralRepository()
    result = await repo.obtener_pares("2024", "4711", None)

    assert len(result) == 1200
    assert mock_client.execute_sql.await_count == 3


@pytest.mark.asyncio
@patch("infrastructure.mcp.behavioral.OracleClient")
async def test_obtener_pares_respects_max_rows(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.execute_sql = AsyncMock()
    page_500 = [{"nit": str(i), "razon_social": f"Test {i}"} for i in range(500)]
    page_200 = [{"nit": str(i), "razon_social": f"Test {i}"} for i in range(200)]
    mock_client.execute_sql.side_effect = [page_500, page_500, page_200]

    repo = OracleBehavioralRepository()
    result = await repo.obtener_pares("2024", "4711", None, page_size=500, max_rows=1200)

    assert len(result) == 1200
    assert mock_client.execute_sql.await_count == 3


@pytest.mark.asyncio
@patch("infrastructure.mcp.behavioral.OracleClient")
async def test_obtener_pares_empty(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.execute_sql = AsyncMock()
    mock_client.execute_sql.return_value = []

    repo = OracleBehavioralRepository()
    result = await repo.obtener_pares("2024", "4711", "COMUN")

    assert result == []
    mock_client.execute_sql.assert_awaited_once()


@pytest.mark.asyncio
@patch("infrastructure.mcp.behavioral.OracleClient")
async def test_obtener_pares_exact_max_rows(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.execute_sql = AsyncMock()
    page = [{"nit": str(i), "razon_social": f"Test {i}"} for i in range(500)]
    mock_client.execute_sql.side_effect = [page, page, page, page]

    repo = OracleBehavioralRepository()
    result = await repo.obtener_pares("2024", "4711", "COMUN", page_size=500, max_rows=2000)

    assert len(result) == 2000
    assert mock_client.execute_sql.await_count == 4

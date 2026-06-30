from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from infrastructure.mcp.oracle_adapter import OracleClient


@patch("infrastructure.mcp.oracle_adapter.settings")
def test_init_settings(mock_settings):
    mock_settings.oracle_host = "192.168.1.1"
    mock_settings.oracle_port = 1522
    mock_settings.oracle_service = "TESTDB"
    mock_settings.oracle_user = "test_user"
    mock_settings.oracle_password = "test_pass"

    client = OracleClient()
    assert client._pool is None


@pytest.mark.asyncio
@patch("infrastructure.mcp.oracle_adapter.settings")
@patch("infrastructure.mcp.oracle_adapter.oracledb")
async def test_initialize_crea_pool(mock_oracledb, mock_settings):
    mock_settings.oracle_host = "192.168.1.1"
    mock_settings.oracle_port = 1521
    mock_settings.oracle_service = "TESTDB"
    mock_settings.oracle_user = "test_user"
    mock_settings.oracle_password = "test_pass"
    mock_settings.oracle_pool_min = 2
    mock_settings.oracle_pool_max = 5
    mock_settings.oracle_pool_timeout = 30

    mock_dsn = MagicMock()
    mock_oracledb.makedsn.return_value = mock_dsn
    mock_oracledb.create_pool_async = AsyncMock(return_value=AsyncMock())

    client = OracleClient()
    await client.initialize()
    mock_oracledb.makedsn.assert_called_once_with("192.168.1.1", 1521, service_name="TESTDB")
    mock_oracledb.create_pool_async.assert_awaited_once()


@pytest.mark.asyncio
@patch("infrastructure.mcp.oracle_adapter.settings")
async def test_execute_sql_retorna_lista_de_dicts(mock_settings):
    _set_mock_settings(mock_settings)

    mock_cursor = AsyncMock()
    mock_cursor.description = [("ID",), ("NAME",)]

    mock_pool = _fake_pool(mock_cursor, [(1, "test")])

    client = OracleClient()
    client._pool = mock_pool
    result = await client.execute_sql("SELECT 1 FROM DUAL")

    assert result == [{"id": 1, "name": "test"}]


@pytest.mark.asyncio
@patch("infrastructure.mcp.oracle_adapter.settings")
async def test_execute_sql_con_bind_params(mock_settings):
    _set_mock_settings(mock_settings)

    mock_cursor = AsyncMock()
    mock_cursor.description = [("NIT",)]

    mock_pool = _fake_pool(mock_cursor, [])

    client = OracleClient()
    client._pool = mock_pool
    result = await client.execute_sql("SELECT 1 FROM DUAL WHERE nit = :nit", {"nit": "123"})

    assert result == []
    mock_cursor.execute.assert_awaited_once_with("SELECT 1 FROM DUAL WHERE nit = :nit", {"nit": "123"})


@pytest.mark.asyncio
async def test_close_cierra_pool():
    import infrastructure.mcp.oracle_adapter as oa

    mock_pool = AsyncMock()
    mock_pool.close = AsyncMock()
    oa._pool = mock_pool

    client = OracleClient()
    client._pool = mock_pool
    await client.close()

    mock_pool.close.assert_awaited_once()


def _set_mock_settings(mock_settings):
    mock_settings.oracle_host = "192.168.1.1"
    mock_settings.oracle_port = 1521
    mock_settings.oracle_service = "TESTDB"
    mock_settings.oracle_user = "test_user"
    mock_settings.oracle_password = "test_pass"
    mock_settings.oracle_pool_min = 2
    mock_settings.oracle_pool_max = 5


def _fake_pool(mock_cursor, fetchall_return):
    mock_cursor.execute = AsyncMock(return_value=mock_cursor)
    mock_cursor.fetchall = AsyncMock(return_value=fetchall_return)
    mock_cursor.close = AsyncMock()

    class FakeConn:
        def cursor(self):
            return mock_cursor

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class FakePool:
        def acquire(self):
            return FakeConn()

    return FakePool()

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
async def reset_pool():
    from infrastructure.persistence.connection import close_pool
    await close_pool()
    yield
    await close_pool()


@pytest.mark.asyncio
async def test_get_pool_crea_pool_una_vez():
    from infrastructure.persistence.connection import close_pool, get_pool

    pool_mock = AsyncMock()

    async def fake_create_pool(**kwargs):
        return pool_mock

    with patch("infrastructure.persistence.connection.asyncpg.create_pool", side_effect=fake_create_pool):
        p1 = await get_pool()
        p2 = await get_pool()

        assert p1 is pool_mock
        assert p2 is pool_mock

    pool_mock.close.assert_not_called()
    await close_pool()


@pytest.mark.asyncio
async def test_close_pool_cierra_y_resetea():
    from infrastructure.persistence.connection import close_pool, get_pool

    pool_mock = AsyncMock()

    async def fake_create_pool(**kwargs):
        return pool_mock

    with patch("infrastructure.persistence.connection.asyncpg.create_pool", side_effect=fake_create_pool):
        await get_pool()
        await close_pool()

        pool_mock.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_verificar_conexion_ok():
    from infrastructure.persistence.connection import close_pool, verificar_conexion

    conn_mock = AsyncMock()
    conn_mock.fetchval = AsyncMock(return_value=1)

    class FakePool:
        async def close(self):
            pass

        def acquire(self):
            return self

        async def __aenter__(self):
            return conn_mock

        async def __aexit__(self, *args):
            pass

    async def fake_create_pool(**kwargs):
        return FakePool()

    with patch("infrastructure.persistence.connection.asyncpg.create_pool", side_effect=fake_create_pool):
        result = await verificar_conexion()
        assert result is True
        conn_mock.fetchval.assert_awaited_once_with("SELECT 1")

    await close_pool()


@pytest.mark.asyncio
async def test_verificar_conexion_fail():
    from infrastructure.persistence.connection import close_pool, verificar_conexion

    async def fake_create_pool(**kwargs):
        raise Exception("DB down")

    with patch("infrastructure.persistence.connection.asyncpg.create_pool", side_effect=fake_create_pool):
        result = await verificar_conexion()
        assert result is False

    await close_pool()

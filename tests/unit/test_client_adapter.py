from unittest.mock import patch

import pytest
from infrastructure.mcp.client_adapter import AGT05MCPClient


@pytest.mark.asyncio
@patch("infrastructure.mcp.client_adapter.paginar_contribuyentes")
async def test_agent_buscar_delega_a_paginar(mock_paginar):
    mock_paginar.return_value = _async_gen([{"nit": "1"}, {"nit": "2"}])

    agent = AGT05MCPClient()
    items = []
    async for item in agent.buscar_contribuyentes(
        vigencia_ini="2024-01-01",
        vigencia_fin="2024-12-31",
        tipo_regimen="COMUN",
        actividades_economicas=["4711"],
        periodo="2024",
    ):
        items.append(item)

    assert len(items) == 2
    assert items[0]["nit"] == "1"
    mock_paginar.assert_called_once()
    call_kwargs = mock_paginar.call_args.kwargs
    assert call_kwargs["vigencia_ini"] == "2024-01-01"
    assert call_kwargs["tipo_regimen"] == "COMUN"
    assert call_kwargs["actividades_economicas"] == ["4711"]


@pytest.mark.asyncio
@patch("infrastructure.mcp.client_adapter.obtener_datos_fiscales")
async def test_agent_obtener_datos_delega(mock_obtener):
    mock_obtener.return_value = {"nit": "9003189639", "razon_social": "TEST"}

    agent = AGT05MCPClient()
    result = await agent.obtener_datos("9003189639", "2024")

    assert result["nit"] == "9003189639"
    mock_obtener.assert_called_once()
    call_args = mock_obtener.call_args
    assert call_args[0][1] == "9003189639"
    assert call_args[0][2] == "2024"


@pytest.mark.asyncio
async def test_agent_close_no_op():
    agent = AGT05MCPClient()
    await agent.close()


async def _async_gen(items):
    for item in items:
        yield item

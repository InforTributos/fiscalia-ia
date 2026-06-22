from domain.errors import NITNoEncontradoError, ProcesoNoEncontradoError, MCPConnectionError
from main import app
from fastapi import APIRouter
from fastapi.testclient import TestClient

client = TestClient(app)


def test_fiscalia_error_retorna_json_estructurado():
    router = APIRouter()

    @router.get("/test-error")
    async def trigger_error():
        raise NITNoEncontradoError("9003189639")

    app.include_router(router, prefix="/_test")

    response = client.get("/_test/test-error")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "NIT_NO_ENCONTRADO"
    assert "9003189639" in data["mensaje"]
    assert "request_id" in data


def test_fiscalia_error_503():
    router = APIRouter()

    @router.get("/test-mcp-error")
    async def trigger_mcp_error():
        raise MCPConnectionError("timeout")

    app.include_router(router, prefix="/_test")

    response = client.get("/_test/test-mcp-error")
    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "MCP_CONNECT_FAIL"

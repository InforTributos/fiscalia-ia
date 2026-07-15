# Design: Tests de caracterizacion del modulo MCP

## Components

### Test files (nuevos)

| Archivo de test | Archivo bajo prueba | Mock de dependencias |
|---|---|---|
| `tests/unit/test_oracle_adapter.py` | `infrastructure/mcp/oracle_adapter.py` | `httpx.AsyncClient`, `mcp.client.streamable_http.streamable_http_client`, `mcp.ClientSession`, `config.settings` |
| `tests/unit/test_pagination.py` | `infrastructure/mcp/pagination.py` | `MCPClient.call_tool` (via AsyncMock) |
| `tests/unit/test_client_adapter.py` | `infrastructure/mcp/client_adapter.py` | `MCPClient`, `pagination.paginar_contribuyentes`, `pagination.obtener_datos_fiscales` |
| `tests/unit/test_analisis_task.py` | `tasks/analisis_task.py` | `ProcesoOrchestrator`, `LLMService`, `PostgresProcesoRepo`, `tasks.retry.with_retry` |
| `tests/unit/test_config.py` | `config.py` | Ninguno (usa monkeypatch de env vars) |

### Fixtures compartidas

```python
# tests/unit/conftest.py (adicion)

@pytest.fixture
def mock_settings():
    """Settings con valores MCP falsos para tests."""
    return {
        "MCP_SERVER_URL": "https://mcp.example.com/mcp/v1/databases/ocid1.test",
        "MCP_TOKEN_URL": "https://mcp.example.com/auth/v1/databases/ocid1.test/token",
        "MCP_DB_USER": "test_user",
        "MCP_DB_PASSWORD": "test_pass",
        "MCP_TIMEOUT": "10",
    }

@pytest.fixture
def fake_mcp_session():
    """Session MCP falsa con call_tool predecible."""
    session = AsyncMock(spec=ClientSession)
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock()
    return session
```

## Data Model

### Mock de token response

```python
FAKE_TOKEN_RESPONSE = {
    "access_token": "eyJhbGciOiJSUzI1NiIs...fake...",
    "token_type": "Bearer",
    "expires_in": 3600,
}
```

### Mock de respuesta EXECUTE_SQL

```python
FAKE_CONTRIBUYENTE_RESPONSE = [
    {
        "nit": "9003189639",
        "razon_social": "COMERCIO XYZ S.A.S.",
        "ciiu": "4711",
        "regimen": "COMUN",
        "rues_estado": "ACTIVO",
    }
]

FAKE_DECLARACIONES_RESPONSE = [
    {"periodo": "2024-B1", "base_gravable": 50000000, "tarifa": 0.008, "impuesto": 400000},
]

FAKE_EXOGENA_RESPONSE = [
    {"periodo": "2024", "ingresos": 120000000},
]
```

## API Contracts (patron de mocking)

Los tests mockean a nivel de modulo usando `@patch`:

```python
@patch("infrastructure.mcp.oracle_adapter.settings")
@patch("infrastructure.mcp.oracle_adapter.streamable_http_client")
@patch("infrastructure.mcp.oracle_adapter.httpx.AsyncClient")
@patch("infrastructure.mcp.oracle_adapter.ClientSession")
def test_call_tool_retorna_json_parsed(mock_session_cls, mock_http_cls, mock_stream_factory, mock_settings):
    # Arrange
    mock_settings.mcp_server_url = "https://mcp.test/v1"
    mock_settings.mcp_token_url = "https://mcp.test/auth/token"
    mock_settings.mcp_db_user = "user"
    mock_settings.mcp_db_password = "pass"
    mock_settings.mcp_timeout = 10
    ...
```

### Mock de streamable_http_client (async generator)

```python
# streamable_http_client es un @asynccontextmanager que yield (read_stream, write_stream)
# Se mockea como:
mock_read = MagicMock()
mock_write = MagicMock()
mock_stream_factory.return_value.__aenter__.return_value = (mock_read, mock_write)
mock_stream_factory.return_value.__aexit__.return_value = None
```

### Mock de httpx.AsyncClient (token POST)

```python
# httpx.AsyncClient se usa como context manager para POST del token
mock_http = AsyncMock()
mock_http_cls.return_value.__aenter__.return_value = mock_http
mock_http.post.return_value.raise_for_status = MagicMock()
mock_http.post.return_value.json.return_value = {"access_token": "fake-token"}
```

### Mock de call_tool

```python
# La respuesta de session.call_tool es un CallToolResult con content=[TextContent(text=...)]
fake_call_result = MagicMock()
fake_call_result.content = [MagicMock()]
fake_call_result.content[0].text = json.dumps({"nit": "123", "razon_social": "TEST"})
mock_session_cls.return_value.__aenter__.return_value.call_tool.return_value = fake_call_result
```

## Dependencies

- `pytest`, `pytest-asyncio` — ya instalados
- `httpx` — ya instalado
- `mcp` SDK v1.28+ — verificar `pip install mcp` disponible
  - Si no esta en CI, los tests usan mock a nivel de modulo y no importan el SDK real
- Sin nuevas dependencias

---
name: error-handling
description: Use when working with error handling — raising FiscalIAError subtypes, adding new error types, modifying the error handler middleware, or mapping errors to HTTP responses.
---

# Error Handling — FiscalIA

## FiscalIAError Hierarchy
All domain errors live in `domain/errors.py`:

```python
class FiscalIAError(Exception):
    codigo_http: int
    codigo: str
    mensaje: str
    request_id: str | None
```

| Error | HTTP | Usage |
|---|---|---|
| `DomainError` | 400 | Validation failures |
| `EntidadNoEncontradaError` | 404 | NIT/proceso not found |
| `ProcesoEnEjecucionError` | 409 | Process already running |
| `LimiteExcedidoError` | 429 | Rate limit hit |
| `MCPError` | 502 | MCP connection/tool failure |
| `LLMError` | 502 | LLM provider failure |
| `InfraestructuraError` | 500 | Unexpected infra errors |

## Error Classification by Layer

| Layer | Example Codes |
|---|---|
| `MCP` | `MCP_TIMEOUT`, `MCP_CONN_REFUSED`, `MCP_PAGE_ERROR` |
| `ORACLE` | `ORACLE_QUERY_FAIL`, `ORACLE_TIMEOUT` |
| `LLM` | `LLM_TIMEOUT`, `LLM_RATE_LIMIT`, `LLM_INVALID_JSON`, `LLM_ALL_PROVIDERS_FAILED` |
| `POSTGRES` | `PG_CONN_ERROR`, `PG_INSERT_FAIL` |
| `VALIDACION` | `CRITERIOS_INVALIDOS`, `NIT_NO_ENCONTRADO` |
| `PROCESO` | `WORKER_TIMEOUT`, `ORCHESTRATION_FAIL` |

## Rules
- NEVER raise `HTTPException` in routers. Raise `FiscalIAError` subtypes.
- The middleware at `middleware/error_handler.py` catches all `FiscalIAError` and returns standardized JSON.
- New error types must extend `FiscalIAError` and define `codigo_http` and `codigo`.

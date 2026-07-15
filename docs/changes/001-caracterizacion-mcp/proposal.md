# Proposal: Tests de caracterizacion del modulo MCP

## Intent

Escribir tests de caracterizacion (unitarios, con mocks) para los 4 archivos del modulo `infrastructure/mcp/` y `tasks/analisis_task.py` que actualmente tienen 0% de cobertura. El codigo ya existe, por lo que el proposito es fijar el comportamiento actual como red de seguridad y elevar la cobertura hacia el quality gate del 80%.

## Scope

- **In scope**:
  - `infrastructure/mcp/oracle_adapter.py` — Test de `MCPClient`: `_get_token()`, `call_tool()`, `close()`, manejo de settings
  - `infrastructure/mcp/pagination.py` — Test de `obtener_datos_fiscales()` y `paginar_contribuyentes()`: construccion de SQL, paginacion via EXECUTE_SQL, ensamblado de datos
  - `infrastructure/mcp/client_adapter.py` — Test de `AGT05MCPClient`: delegacion a pagination, construccion con MCPClient
  - `infrastructure/mcp/classify.py` — YA TIENE tests (test_mcp_client.py + test_classify.py), verificar cobertura y complementar edge cases
  - `tasks/analisis_task.py` — Test del loop de background task: iteracion de rows, manejo de errores por NIT, cambio de estados
- **Out of scope**:
  - LLM providers (anthropic, openai, nvidia, huggingface) — requieren API keys reales
  - Tests de integracion con Oracle MCP real — no disponible aun
  - Tests de integracion con PostgreSQL real — no disponible aun
  - Refactoring de codigo existente (solo tests)
  - Cobertura de `config.py` — ya tiene test_config.py

## Approach

**Characterization testing** (TDD retroactivo): Escribir tests que documenten y verifiquen el comportamiento actual del codigo, mockeando todas las dependencias externas (httpx, mcp session, settings).

Cada test:
1. Mockea las dependencias externas (httpx.AsyncClient, streamable_http_client, settings)
2. Configura returns predecibles (token falso, respuestas SQL sinteticas)
3. Ejecuta la funcion bajo prueba
4. Verifica que la salida y los side effects coinciden con lo esperado

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tests no reflejan comportamiento real de Oracle MCP | Alta | Medio | Documentar queries SQL exactas y formato de respuesta esperado en los tests |
| Dependencia del SDK mcp v1.28+ no instalado en CI | Media | Alto | Verificar que `pip install mcp` funcione en CI; si falla, mockear a nivel de modulo |
| Mock de `streamable_http_client` es complejo (async generator) | Alta | Bajo | Mockear a nivel de modulo en lugar de instanciar objetos reales |

## Affected Components

- `tests/unit/test_oracle_adapter.py` (nuevo)
- `tests/unit/test_pagination.py` (nuevo)
- `tests/unit/test_client_adapter.py` (nuevo)
- `tests/unit/test_analisis_task.py` (nuevo)
- `tests/unit/test_classify.py` (posible adicion de edge cases)
- `tests/unit/test_config.py` (adicion de tests para nuevas vars MCP)

# Project Rules

## Stack
- Python 3.14+
- FastAPI para REST
- asyncpg para PostgreSQL
- Provider SDKs: anthropic, openai, huggingface_hub
- fastmcp para MCP Client (stdio)
- pydantic + pydantic-settings para schemas y config
- tenacity para retry

## Code Style
- Type hints obligatorios en todas las funciones
- Nombres en inglés para código, español para strings de dominio
- Máximo 120 caracteres por línea
- imports: estándar, terceros, locales (separados por línea vacía)
- ruff como linter y formateador

## Commits
- Formato: `{hat}: {unit} - {mensaje}`
- Ejemplo: `builder: U-03 - implementar endpoint POST /proceso`

## Testing
- AAA Pattern (Arrange, Act, Assert) — obligatorio
- Tests en `tests/unit/` mirror de `microservice/`
- Mocks para repositorios (PostgresProcesoRepo), no parchear queries directo
- Repositorios mockeados vía fixture (ver `test_orchestrator.py`)
- pytest como runner, pytest-asyncio para tests async
- Objetivo: cobertura ≥ 80%

## Variables de Entorno
- No hardcodear secrets
- Usar `.env` para desarrollo, OCI Vault para producción
- Validar al startup: placeholder `changeme` produce error
- Documentar en `.env.example`

## Errores
- Jerarquía `FiscalIAError` con código HTTP por tipo
- Middleware `error_handler.py` captura y retorna JSON estandarizado
- Logging estructurado (JSON) con `request_id`
- Retry con tenacity para llamadas externas (LLM, MCP, DB)

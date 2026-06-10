# Project Rules

## Stack
- Python 3.11+
- FastAPI para REST
- LangGraph para orquestación de agentes
- python-oracledb para Oracle
- Anthropic SDK para Claude API

## Code Style
- Type hints obligatorios en todas las funciones
- Docstrings en funciones públicas
- Nombres en inglés para código, español para comentarios de dominio
- Máximo 80 caracteres por línea
- imports: estándar, terceros, locales (separados por línea vacía)

## Commits
- Formato: `{hat}: {unit} - {mensaje}`
- Ejemplo: `builder: U-03 - implementar orquestador LangGraph`

## Testing
- AAA Pattern (Arrange, Act, Assert)
- Tests en `tests/` mirror de `microservice/`
- Mocks para Oracle y Claude API
- pytest como runner

## Variables de Entorno
- No hardcodear secrets
- Usar `.env` para desarrollo, OCI Vault para producción
- Documentar en `.env.example`

## Errores
- FastAPI exception handlers globales
- Logging estructurado (JSON)
- Retry con tenacity para llamadas externas

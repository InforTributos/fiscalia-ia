# Contribuyendo a FiscalIA

Gracias por tu interés en contribuir al microservicio de fiscalización ICA.

## Stack

- **Lenguaje:** Python 3.11+
- **Framework:** FastAPI
- **Base de datos:** PostgreSQL 16+ (asyncpg)
- **LLM:** Agnóstico (Anthropic, OpenAI, NVIDIA NIM, HuggingFace)
- **Tests:** pytest + pytest-asyncio + factory-boy
- **Linter:** ruff (line-length 120, comillas dobles)
- **Arquitectura:** Hexagonal (Ports & Adapters) + DDD

## Convenciones de código

1. **Linter:** `ruff check microservice/ tests/` — cero errores antes de commitear.
2. **Formato:** `ruff format microservice/ tests/` — line-length 120, comillas dobles.
3. **Imports:** Standard library → third-party → local, orden alfabético.
4. **Type hints:** Obligatorios en todas las funciones públicas.
5. **Docstrings:** Solo en módulos y clases públicas (sin comentarios internos).
6. **Tests:** Deben seguir AAA (Arrange-Act-Assert). Repositorios se mockean vía fixtures, no con `@patch` directo a queries.
7. **Errores:** Usar la jerarquía `FiscalIAError` del dominio. Nunca lanzar `HTTPException` directo en routers.

## Cómo contribuir

### 1. Reportar bugs

Abrir un issue describiendo:
- Comportamiento esperado vs actual
- Pasos para reproducir
- Versión y entorno

### 2. Proponer cambios

1. Crear un fork del repositorio.
2. Crear una rama descriptiva: `fix/descripcion` o `feat/descripcion`.
3. Hacer los cambios asegurando cobertura ≥ 80%.
4. Correr tests localmente.
5. Enviar un Pull Request a `main`.

### 3. Pull Requests

- Título descriptivo con prefijo (`feat:`, `fix:`, `docs:`, `refactor:`).
- Cuerpo explicando qué cambia y por qué.
- Enlazar issues relacionados.
- Una vez aprobado, se hace squash merge.

## Tests

```bash
# Unit tests
pytest tests/unit/ -v --cov=microservice --cov-report=term

# Coverage gate
pytest --cov=microservice --cov-fail-under=80

# Lint
ruff check microservice/ tests/

# Format check
ruff format --check microservice/ tests/
```

## Estructura de directorios

```
domain/ports/       # ABCs (interfaces)
domain/services/    # Lógica pura de dominio
domain/errors.py    # Jerarquía de errores
application/use_cases/  # Orquestación
infrastructure/llm/     # Proveedores LLM concretos
infrastructure/persistence/  # PostgreSQL (asyncpg)
infrastructure/mcp/     # Cliente MCP Oracle
middleware/             # Error handler, logging, rate limiter
routers/                # Endpoints FastAPI
tests/unit/             # Tests unitarios
```

## Licencia

Al contribuir, aceptas que tus cambios se distribuyan bajo la licencia MIT del proyecto.

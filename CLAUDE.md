# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto: FiscalIA

Microservicio Python para análisis de fiscalización del Impuesto de Industria y Comercio (ICA) en Valledupar. Arquitectura hexagonal + DDD con 4 proveedores LLM con fallback automático, PostgreSQL async, y cliente MCP para Oracle.

## ⚠️ LECTURA OBLIGATORIA

**Antes de cualquier cambio, investigación o feature:** Lee en este orden:

1. **Este archivo (CLAUDE.md)** — comandos, arquitectura, convenciones, gotchas
2. **AGENTS.md COMPLETAMENTE** — fuente de verdad técnica: arquitectura detallada, error classification, MCP contract, process states, rate limiting, conventions, gotchas
3. **MEMORY/TODO.md** — qué trabajo está pendiente, tech debt, tareas en progreso
4. **Si trabajas en LLM:** `docs/06-llm-configuracion.md` (4 tiers, fallback chain)
5. **Si trabajas en datos/modelo:** `docs/02-modelo-datos.md`
6. **Si trabajas en MCP:** `docs/03-contrato-mcp.md`
7. **Si necesitas big picture:** `docs/01-arquitectura.md` (diagramas, flujos)

AGENTS.md es la fuente de verdad técnica más detallada. Cada feature/bug que toques probablemente dependa de algo que está documentado ahí.

## Comandos Esenciales

### Lint, Format, Tests

```bash
# Lint (ruff, line-length 120, comillas dobles)
ruff check microservice/ tests/

# Auto-format
ruff format microservice/ tests/

# Unit tests (PYTHONPATH es crítico — apunta a microservice/)
PYTHONPATH=microservice pytest tests/unit/ -v

# Test individual
PYTHONPATH=microservice pytest tests/unit/test_crosscheck.py::test_srf_classification -v

# Coverage (80% gate)
PYTHONPATH=microservice pytest tests/unit/ --cov=microservice --cov-fail-under=80 --cov-report=term

# Run server (desde microservice/)
cd microservice && uvicorn main:app --reload
```

**Crítico:** `PYTHONPATH=microservice` es obligatorio en todos los commands pytest. El root del proyecto es `microservice/`, no la raíz del repo.

### Desarrollo rápido

```bash
# Format + Lint check
ruff format microservice/ tests/ && ruff check microservice/ tests/

# Full test pipeline
PYTHONPATH=microservice pytest tests/unit/ -v --cov=microservice --cov-fail-under=80
```

## Arquitectura

**Hexagonal (Ports & Adapters) + DDD.**

```
routers/                    ← FastAPI endpoints (inbound adapters)
    ├── main.py             ← App factory, lifespan, middleware setup
    ├── analisis.py         ← POST /analizar/{nit}
    ├── proceso.py          ← POST /proceso, GET /proceso/{id}
    └── schemas/            ← Pydantic request/response models

application/use_cases/      ← Orquestadores
    └── orquestar_proceso.py ← ProcesoOrchestrator (orchestrates domain + infra)

domain/                     ← Lógica pura, cero deps externas
    ├── ports/              ← ABCs: LLMProvider, ContribuyenteRepo, ProcesoRepo
    ├── services/           ← CrosscheckService (SRF), InconsistencyService
    └── errors.py           ← Jerarquía FiscalIAError con códigos HTTP

infrastructure/             ← Adaptadores concretos (outbound)
    ├── llm/                ← 4 providers LLM (Anthropic, OpenAI, NVIDIA NIM, HF)
    │                         + llm_service.py (fallback chain + tenacity)
    ├── persistence/        ← asyncpg pool + 17 queries SQL
    └── mcp/                ← Oracle MCP stdio client + pagination + classify

middleware/                 ← Error handler centralizado, logging, rate limiter
```

### Flujo crítico: POST /analizar/{nit}

1. **Router** (`routers/analisis.py`) valida NIT, instantiates repos + LLM
2. **Orchestrator** (`ProcesoOrchestrator`) orquesta:
   - MCP: Fetch datos fiscales via `oracle_adapter`
   - Domain: `crosscheck_service.srf_4_componentes()` → classification
   - LLM: `llm_service` con fallback (Anthropic → OpenAI → NVIDIA NIM → HF)
   - Persistence: Guarda resultado en PostgreSQL
3. **Error Handler** (`middleware/error_handler.py`) captura `FiscalIAError` → HTTP response

**Inyección de dependencias:** Repos + LLM se pasan por constructor, no por DI framework. Routers hacen `repo = PostgresProcesoRepo()` a nivel de módulo.

## Convenciones Críticas

### Errores
- **Nunca** lanzar `HTTPException` directamente en routers. Usar `FiscalIAError` subtypes (definidos en `domain/errors.py`).
- `error_handler.py` mapea `FiscalIAError` → HTTP status + JSON response.
- Cada error tiene un código único (ej. `LLM_TIMEOUT`, `MCP_CONN_REFUSED`, `PG_CONN_ERROR`).

### Tests
- **AAA pattern:** Arrange-Act-Assert.
- **Repos mocked via fixtures**, no `@patch("queries.*")`. Ver `conftest.py`.
- Coverage target: 80%. Sin DB/MCP/LLM reales, capped ~72%.
- Pytest markers: `@pytest.mark.integration` para tests que requieren deps externas.

### Config
- **Fuente de verdad:** `.env.example` — names, formats, defaults.
- Pydantic-settings lee `.env` at startup.
- Validación: rechaza `changeme` placeholders en API keys / DB password.
- Pool asyncpg: configurable via `POOL_MIN_SIZE`, `POOL_MAX_SIZE`, `POOL_TIMEOUT`.
- **Tiers LLM:** `LLM_TIER1_*`, `LLM_TIER2_*`, `LLM_TIER3_*` (tier 1 es pagado, tier 2-3 gratis).

### Code Style
- **Ruff:** line-length 120, comillas dobles, rules `E, F, I, N, W, UP`.
- **Type hints:** Obligatorios en funciones públicas.
- **Docstrings:** Solo módulos + clases públicas. Función pura ≠ docstring.
- **Imports:** stdlib → third-party → local, alfabético.

## Gotchas & Trampas

1. **`PYTHONPATH=microservice`** — Olvidarlo en pytest → import errors. Es obligatorio.
2. **Repos a nivel de módulo en routers** — `repo = PostgresProcesoRepo()` se ejecuta al importar, no lazy. Normal by design.
3. **Pool lifecycle en lifespan** — Si cambias `main.py`, asegúrate que pool se init/close via `lifespan()`.
4. **Windows CRLF warnings** — `.gitattributes` no está configurado. Safe to ignore.
5. **Coverage gate ~72% sin DB** — Algunos paths inalcanzables sin PostgreSQL + MCP + LLM reales.
6. **`orquestar_proceso.py` hardcodes `periodo="2024"`** — Needs parametrizing (TODO in MEMORY/TODO.md).
7. **`microservice/config.py` en root** — No en un package `config/`. Raro pero by design.

## Documentación

- **01-arquitectura.md** — Big picture, diagramas, flujos.
- **03-contrato-mcp.md** — MCP contract (buscar_contribuyentes, obtener_datos_fiscales).
- **06-llm-configuracion.md** — Detalles de 4 tiers LLM + fallback.
- **09-plan-desarrollo.md** — Roadmap, status, pending work.

Start con `01-arquitectura.md` si necesitas entender el sistema completo.

## Project Memory (Obsidian Vault)

`MEMORY/` abre como Obsidian vault. Contains:
- **INDEX.md** — Entry point (decisiones, contexto, gotchas).
- **TODO.md** — Tech debt + tareas pendientes. **Agents actualizan esto después de cada tarea.**
- **DECISIONS.md** — ADRs con rationale y alternativas.
- **GOTCHAS.md** — Lecciones aprendidas.

**Antes de empezar nuevo trabajo, revisar `MEMORY/TODO.md`.**

## AI-DLC Methodology

Project usa Hat-Based AI-DLC. Reglas + domain knowledge en `.ai-dlc/`:
- `config.yml` — Metadata, 6 units (U-01…U-06), quality gates.
- `knowledge/domain.md` — ICA domain, 6 agentes (AGT-00…AGT-05), SRF, MCP contract.
- `rules/project.md` — Commit format (`{hat}: {unit} - {msg}`), code style, testing mandates.

## Configuración Inicial (si necesitas trabajar en el servidor)

```bash
# Dependencies
pip install -r microservice/requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx factory-boy hypothesis pytest-html

# Config
cp .env.example .env
# Edit .env con PostgreSQL_* y LLM_TIER* credentials

# Run
cd microservice && uvicorn main:app --reload
# Swagger en http://localhost:8000/docs
```

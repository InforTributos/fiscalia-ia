# AGENTS.md

## Quick Start

```bash
pip install -r microservice/requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx factory-boy hypothesis pytest-html
cp .env.example .env  # edit with real POSTGRES_* and LLM_TIER* keys
uvicorn main:app --reload  # from microservice/ directory
```

## Commands

| Action | Command |
|---|---|
| Lint | `ruff check microservice/ tests/` |
| Format | `ruff format microservice/ tests/` |
| All tests | `PYTHONPATH=microservice pytest tests/unit/ -v` |
| Single test | `PYTHONPATH=microservice pytest tests/unit/test_crosscheck.py -v` |
| Coverage | `PYTHONPATH=microservice pytest tests/unit/ --cov=microservice --cov-report=term` |
| Coverage gate | `PYTHONPATH=microservice pytest tests/unit/ --cov=microservice --cov-fail-under=80` |

**PYTHONPATH=microservice is required** for all pytest commands — the project root is `microservice/`, not the repo root.

## Architecture

Hexagonal (Ports & Adapters) + DDD. Capas:

- `domain/` — Pure logic: `services/crosscheck_service.py` (SRF), `services/inconsistency_service.py`, `errors.py`. Zero external deps.
- `domain/ports/` — ABCs: `LLMProvider`, `ContribuyenteRepo`, `ProcesoRepo`.
- `application/use_cases/` — `orquestar_proceso.py` (orchestrator, accepts repos by constructor).
- `infrastructure/llm/` — 4 providers: Anthropic, OpenAI, NVIDIA NIM, HuggingFace. Fallback via `llm_service.py`.
- `infrastructure/persistence/` — `connection.py` (asyncpg pool), `queries.py` (17 CRUD fns), `repositorio_*.py` (concrete repos).
- `infrastructure/mcp/` — Oracle MCP adapter stdio + pagination + classify.
- `routers/` — FastAPI endpoints. Routers instantiate `PostgresProcesoRepo()` directly.
- `middleware/` — `error_handler.py` (catches `FiscalIAError`), `logging.py`, `rate_limiter.py`.
- `tasks/` — `analisis_task.py` (background), `retry.py` (tenacity).
- `cache/` — `response_cache.py` (in-memory TTL).

## Key Conventions

- **Config**: `config.py` uses `pydantic-settings` reading `.env`. Startup validates no `changeme` placeholders in API keys or DB password.
- **Errors**: Never raise `HTTPException` in routers. Raise `FiscalIAError` subtypes — `error_handler.py` maps them to HTTP responses.
- **Tests**: AAA (Arrange-Act-Assert). Repos are **mocked via fixtures** (`mock_repo`), not patched via `@patch("queries.*")`. The `conftest.py` adds `microservice/` to `sys.path`.
- **Linting**: ruff, line-length 120, double quotes. Rules: `E, F, I, N, W, UP`.
- **Pool**: asyncpg pool lifecycle managed by FastAPI lifespan in `main.py`. Configurable via `POOL_MIN_SIZE`, `POOL_MAX_SIZE`, `POOL_TIMEOUT` env vars.
- **Routers import repos at module level**: `repo = PostgresProcesoRepo()` — not via DI framework.
- **Config env vars**: `LLM_TIER1_*`, `LLM_TIER2_*`, `LLM_TIER3_*`, `POSTGRES_*`. `.env.example` is the source of truth for naming.
- **`orquestar_proceso.py`** hardcodes `periodo="2024"` — needs parametrizing.

## Gotchas

- Coverage caps at ~72% without real PostgreSQL/MCP/LLM — the `--cov-fail-under=80` gate only passes in CI with mocked deps.
- `microservice/api/` was deleted in the V2 refactor — only `microservice/routers/` exists now.
- Windows: `CRLF` warnings in git are normal (`.gitattributes` not set). Ignore them.
- `microservice/config.py` is at the `microservice/` root, not in a `config/` package.
- All routers use `repo = PostgresProcesoRepo()` at module import time — no lazy init.
- `docs/03-contrato-plsql.md` was deleted; replaced by `docs/03-contrato-mcp.md`.

## Process States

```
PENDIENTE → PREFILTRANDO → PREFILTRADO_COMPLETADO → EN_COLA → EN_PROCESO → COMPLETADO | ERROR
```

| State | Meaning |
|---|---|
| `PENDIENTE` | Process created, waiting for execution |
| `PREFILTRANDO` | MCP fetching NITs |
| `PREFILTRADO_COMPLETADO` | NITs classified, IA analysis queued |
| `EN_COLA` | Waiting for available worker |
| `EN_PROCESO` | IA analysis running |
| `COMPLETADO` | All NITs analyzed |
| `INTERRUMPIDO` | Container restarted mid-process (recoverable) |
| `ERROR` | Fatal error |

## Error Classification

Errors are classified by layer with specific codes:

| Layer | Example Codes |
|---|---|
| `MCP` | `MCP_TIMEOUT`, `MCP_CONN_REFUSED`, `MCP_PAGE_ERROR` |
| `ORACLE` | `ORACLE_QUERY_FAIL`, `ORACLE_TIMEOUT` |
| `LLM` | `LLM_TIMEOUT`, `LLM_RATE_LIMIT`, `LLM_INVALID_JSON`, `LLM_ALL_PROVIDERS_FAILED` |
| `POSTGRES` | `PG_CONN_ERROR`, `PG_INSERT_FAIL` |
| `VALIDACION` | `CRITERIOS_INVALIDOS`, `NIT_NO_ENCONTRADO` |
| `PROCESO` | `WORKER_TIMEOUT`, `ORCHESTRATION_FAIL` |

Granularity: timeout LLM = 1 error per NIT, multiple validations = multiple errors per NIT.

## Rate Limiting

| Endpoint | Limit | Window |
|---|---|---|
| `POST /proceso` | 10 req | per minute per IP |
| `GET /proceso/{id}/status` | 60 req | per minute per IP |
| `GET /proceso/{id}/results` | 30 req | per minute per IP |
| `GET /proceso/{id}/errors` | 30 req | per minute per IP |
| `POST /analizar/{nit}` | 5 req | per minute per IP |
| `GET /health` | unlimited | — |

## MCP Contract

The service does NOT connect to Oracle directly. All fiscal data is obtained via MCP Server (stdio).

**`buscar_contribuyentes`** — Get candidate NITs by criteria:
`vigencia_ini`, `vigencia_fin`, `tipo_regimen`, `actividades_economicas`, `periodo`, `page`, `page_size`

**`obtener_datos_fiscales`** — Get full fiscal data for a NIT:
`nit`, `periodo` → returns `razon_social`, `ciiu`, `regimen`, `declaraciones_ica`, `exogena_dian`, `rues_estado`

Post-MCP classification: no ICA declarations → **OMISO**, declarations match exogena → **EXACTO**, anomalies → **INEXACTO**.

## Docs

Start with `docs/01-arquitectura.md` for the big picture. `docs/09-plan-desarrollo.md` has the roadmap and current status (116 tests, 72% coverage).

## Project Memory

Open `MEMORY/` as an **Obsidian vault** for graph view, tag filtering, and full-text search.

- **MEMORY/INDEX.md** — Entry point for project memory (decisions, context, gotchas)
- **MEMORY/TODO.md** — Tech debt and pending tasks. **Agents update this after each task.**
- **MEMORY/DECISIONS.md** — Architectural decisions with rationale and alternatives
- **MEMORY/GOTCHAS.md** — Lessons learned and non-obvious behaviors

Check `MEMORY/TODO.md` before starting new work. Update `MEMORY/TODO.md` when completing or discovering tasks.

## AI-DLC

Project uses AI-DLC Hat-Based methodology. Domain knowledge, quality gates, and detailed rules live in `.ai-dlc/`:
- `config.yml` — project metadata, 6 units (U-01…U-06), quality gates
- `knowledge/domain.md` — ICA domain, agentes (AGT-00…AGT-05), SRF, MCP contract
- `rules/project.md` — commit format (`{hat}: {unit} - {msg}`), code style, testing mandates

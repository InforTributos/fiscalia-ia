# AGENTS.md

Microservice that orchestrates AI agents for ICA (Industry and Commerce Tax) enforcement in Valledupar, Colombia. Hexagonal architecture with LLM-agnostic provider chain, Oracle direct connection, and PostgreSQL persistence. Operates under Human-in-the-Loop (HITL) supervision — human review is mandatory for audit finding quality.

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
| All tests | `PYTHONPATH=microservice pytest tests/unit/ tests/integration/ --ignore=tests/integration/test_llm_real.py -v` |
| Single test | `PYTHONPATH=microservice pytest tests/unit/test_crosscheck.py -v` |
| Coverage | `PYTHONPATH=microservice pytest tests/unit/ --cov=microservice --cov-report=term` |
| Coverage gate | `PYTHONPATH=microservice pytest tests/unit/ --cov=microservice --cov-fail-under=80` |

**PYTHONPATH=microservice is required** for all pytest commands — the project root is `microservice/`, not the repo root.

## Architecture

Hexagonal (Ports & Adapters) + DDD. Layers:

- `domain/` — Pure logic: `services/crosscheck_service.py` (SRF), `services/inconsistency_service.py`, `errors.py`. Zero external deps.
- `domain/ports/` — ABCs: `LLMProvider`, `ContribuyenteRepo`, `ProcesoRepo`, `LookupRepository`.
- `application/use_cases/` — `orquestar_proceso.py` (orchestrator, accepts repos by constructor).
- `infrastructure/llm/` — 4 providers: Anthropic, OpenAI, NVIDIA NIM, HuggingFace. Fallback via `llm_service.py`.
- `infrastructure/persistence/` — `connection.py` (asyncpg pool), `queries.py` (17 CRUD fns), `repositorio_proceso.py`, `repositorio_lookup.py`.
- `infrastructure/mcp/` — `oracle_adapter.py` (OracleClient, async oracledb pool), `pagination.py` (4 discovery generators), `classify.py`.
- `routers/` — FastAPI endpoints. Routers instantiate `PostgresProcesoRepo()` directly.
- `middleware/` — `error_handler.py` (catches `FiscalIAError`), `logging.py`, `rate_limiter.py`.
- `tasks/` — `analisis_task.py` (background), `retry.py` (tenacity).
- `cache/` — `response_cache.py` (in-memory TTL).

## Reading Order

Before any change, read in this order:

1. **AGENTS.md** (this file) — source of truth: architecture, conventions, errors, gotchas
2. **MEMORY/TODO.md** — pending work, tech debt, tasks in progress
3. By work area:
   - **LLM**: `docs/06-llm-configuracion.md`
   - **Data model**: `docs/02-modelo-datos.md`
   - **MCP/Oracle**: `docs/03-contrato-mcp.md`
   - **Big picture**: `docs/01-arquitectura.md`

## Key Conventions

- **Config**: `config.py` uses `pydantic-settings` reading `.env`. Startup validates no `changeme` placeholders in API keys or DB password.
- **Errors**: Never raise `HTTPException` in routers. Raise `FiscalIAError` subtypes — `error_handler.py` maps them to HTTP responses.
- **Tests**: AAA (Arrange-Act-Assert). Repos are **mocked via fixtures** (`mock_repo`), not patched via `@patch("queries.*")`. The `conftest.py` adds `microservice/` to `sys.path`. Tests requiring external deps use `@pytest.mark.integration`.
- **Type hints**: Mandatory in public functions.
- **Docstrings**: Only modules + public classes. Pure functions do not require docstrings.
- **Imports**: stdlib → third-party → local, alphabetical.
- **Linting**: ruff, line-length 120, double quotes. Rules: `E, F, I, N, W, UP`.
- **Pool**: asyncpg pool lifecycle managed by FastAPI lifespan in `main.py`. Configurable via `POOL_MIN_SIZE`, `POOL_MAX_SIZE`, `POOL_TIMEOUT` env vars.
- **Routers import repos at module level**: `repo = PostgresProcesoRepo()` — not via DI framework.
- **Config env vars**: `LLM_TIER1_*`, `LLM_TIER2_*`, `LLM_TIER3_*`, `POSTGRES_*`. `.env.example` is the source of truth for naming.
- **LLM Tiers**: Tier 1 (paid, Anthropic/OpenAI), Tier 2 (free, NVIDIA NIM), Tier 3 (free, HuggingFace). See `docs/06-llm-configuracion.md`.
- **`orquestar_proceso.py`** receives `periodo` from `criteria` — no longer hardcoded.

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

Granularity: 1 error per NIT for LLM timeouts, multiple errors per NIT for validation failures.

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

The service DOES connect to Oracle directly via `oracledb` pool (async). See `docs/03-contrato-mcp.md` for details.

**Pre-filtro (batch)**: `tasks/analisis_task.py:pre_filtrar()` runs 4 discovery queries:
- `obtener_omisos_conocidos` — registered taxpayers without ICA declarations
- `obtener_omisos_desconocidos` — DIAN-detected taxpayers not in municipal registry
- `obtener_inexactos_ciiu` — CIIU declaration vs DIAN mismatch
- `obtener_inexactos_retenciones` — withholding discrepancies > threshold

Post-discovery classification: no ICA declarations → **OMISO**, anomalies → **INEXACTO**.

## Docs

Start with `docs/01-arquitectura.md` for the big picture. `docs/09-plan-desarrollo.md` has the roadmap and current status (192 tests, 72% coverage).

## Project Memory

Open `MEMORY/` as an **Obsidian vault** for graph view, tag filtering, and full-text search.

- **MEMORY/INDEX.md** — Entry point for project memory (decisions, context, gotchas)
- **MEMORY/TODO.md** — Tech debt and pending tasks. **Agents update this after each task.**
- **MEMORY/CONTEXT.md** — Current session state and active work context
- **MEMORY/DECISIONS.md** — Architectural decisions with rationale and alternatives
- **MEMORY/GOTCHAS.md** — Lessons learned and non-obvious behaviors

**Before starting new work**: read `MEMORY/TODO.md` and `MEMORY/CONTEXT.md`.
**After completing work**: update `MEMORY/TODO.md` with progress, add entries to `MEMORY/DECISIONS.md` or `MEMORY/GOTCHAS.md` as relevant.

## AI-DLC

Project uses AI-DLC Hat-Based methodology. Domain knowledge, quality gates, and detailed rules live in `.ai-dlc/`:
- `config.yml` — project metadata, 6 units (U-01…U-06), quality gates
- `knowledge/domain.md` — ICA domain, agents (AGT-00…AGT-05), SRF, MCP contract
- `rules/project.md` — commit format (`{hat}: {unit} - {msg}`), code style, testing mandates
- `hats/` — role-specific prompts (builder, implementer, planner, reviewer, test-writer)

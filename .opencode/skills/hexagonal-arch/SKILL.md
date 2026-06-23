---
name: hexagonal-arch
description: Use when writing or reviewing code that touches the hexagonal architecture — domain ports, infrastructure adapters, dependency direction, error handling layer, or the FastAPI router wiring.
---

# Hexagonal Architecture (Ports & Adapters) — FiscalIA

## Layer Rules

```
domain/          → Pure Python. ZERO external dependencies.
  ports/         → ABCs only (LLMProvider, ContribuyenteRepo, ProcesoRepo)
  services/      → Pure business logic (crosscheck_service, inconsistency_service)
  errors.py      → FiscalIAError hierarchy

application/
  use_cases/     → Orchestration (orquestar_proceso.py). Accepts repos via constructor.

infrastructure/
  llm/            → Concrete providers + LLMService (fallback chain)
  persistence/    → asyncpg connection, queries, repositorio_* (concrete repos)
  mcp/            → Oracle adapter, pagination, classify

routers/          → FastAPI endpoints. Instantiates PostgresProcesoRepo() at module level.

middleware/       → error_handler, logging, rate_limiter

cache/            → response_cache (in-memory TTL)
```

## Critical Constraints
- `domain/` MUST NOT import from `infrastructure/`, `routers/`, or `middleware/`
- `domain/ports/` are ABCs, never concrete implementations
- Errors in `domain/errors.py` are `FiscalIAError` subtypes — never `HTTPException`
- Routers raise `FiscalIAError`, the middleware maps to HTTP responses

## Wiring
- `main.py`: FastAPI app factory with lifespan (pool lifecycle)
- Routers: `repo = PostgresProcesoRepo()` at module import time (no DI framework)
- `orquestar_proceso.py`: accepts repos by constructor

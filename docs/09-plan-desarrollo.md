# Plan de Desarrollo — FiscalIA Microservicio OCI

> **Versión:** 2.0.0  
> **Metodología:** AI-DLC Hat-Based  
> **Arquitectura:** Hexagonal (Ports & Adapters) + DDD

---

## Estado Actual

| Métrica | Valor |
|---|---|
| Fases completadas | F-01 a F-07 ✅ |
| Tests unitarios | 116 (todos pasando) |
| Cobertura | 72% (cap: ~72% sin DB/MCP/LLM reales) |
| Ruff linting | 0 errores (config 120 chars) |
| Pool PostgreSQL | asyncpg — min=4, max=20, timeout=5 (configurable) |
| Pendiente externo | MCP Oracle real + conexión (equipo APEX) |

---

## F-01: Fundación Hexagonal (Semana 1) ✅

**Objetivo:** Estructura base, conexión PostgreSQL y health endpoint funcional.

| # | Tarea | Archivos | Estado |
|---|---|---|---|
| 1.1 | Crear `config.py` con variables | `microservice/config.py` | ✅ |
| 1.2 | Pool de conexiones PostgreSQL | `microservice/infrastructure/persistence/connection.py` | ✅ |
| 1.3 | Health endpoint | `microservice/routers/health.py` | ✅ |
| 1.4 | FastAPI app factory + lifespan | `microservice/main.py` | ✅ |
| 1.5 | Error handler centralizado | `microservice/middleware/error_handler.py` | ✅ |
| 1.6 | Dockerfile + docker-compose | `Dockerfile`, `docker-compose.yml` | ✅ |
| 1.7 | Tests de health | `tests/unit/test_health.py` | ✅ |

---

## F-02: Domain + Persistencia (Semana 2) ✅

**Objetivo:** Puerto de dominio, queries PostgreSQL, repositorios concretos.

| # | Tarea | Archivos | Estado |
|---|---|---|---|
| 2.1 | Ports (ABCs) | `domain/ports/contribuyente_repo.py`, `proceso_repo.py`, `llm_port.py` | ✅ |
| 2.2 | Queries PostgreSQL | `infrastructure/persistence/queries.py` (19 funciones) | ✅ |
| 2.3 | Repositorio proceso | `infrastructure/persistence/repositorio_proceso.py` | ✅ |
| 2.4 | Repositorio contribuyente | `infrastructure/persistence/repositorio_contribuyente.py` | ✅ |
| 2.5 | Domain services (SRF) | `domain/services/crosscheck_service.py` | ✅ |
| 2.6 | Domain services (riesgo) | `domain/services/inconsistency_service.py` | ✅ |
| 2.7 | Domain errors | `domain/errors.py` | ✅ |

---

## F-03: Endpoints REST (Semana 3) ✅

**Objetivo:** Todos los endpoints REST con schemas Pydantic.

| # | Tarea | Archivos | Estado |
|---|---|---|---|
| 3.1 | POST /proceso | `microservice/routers/proceso.py` | ✅ |
| 3.2 | GET /proceso/{id}/status | `microservice/routers/status.py` | ✅ |
| 3.3 | GET /proceso/{id}/results | `microservice/routers/results.py` | ✅ |
| 3.4 | GET /proceso/{id}/errors | `microservice/routers/errors.py` | ✅ |
| 3.5 | POST /analizar/{nit} | `microservice/routers/analisis.py` | ✅ |
| 3.6 | GET /health | `microservice/routers/health.py` | ✅ |
| 3.7 | Schemas | `schemas/proceso.py`, `status.py`, `results.py`, `errors.py` | ✅ |
| 3.8 | Tests endpoints | `tests/unit/test_proceso_router.py`, `test_status.py`, `test_results.py` | ✅ |

---

## F-04: MCP + Background Tasks (Semana 4) ✅

**Objetivo:** Conexión MCP, paginación, clasificación y tareas asíncronas.

| # | Tarea | Archivos | Estado |
|---|---|---|---|
| 4.1 | MCP Client | `infrastructure/mcp/oracle_adapter.py` | ✅ |
| 4.2 | Paginación | `infrastructure/mcp/pagination.py` | ✅ |
| 4.3 | Clasificación MCP | `infrastructure/mcp/classify.py` | ✅ |
| 4.4 | Background task | `tasks/analisis_task.py` | ✅ |
| 4.5 | Retry | `tasks/retry.py` | ✅ |
| 4.6 | Orquestador | `application/use_cases/orquestar_proceso.py` | ✅ |
| 4.7 | Tests | `tests/unit/test_orchestrator.py`, `test_mcp_client.py` | ✅ |

---

## F-05: LLM Service + Fallback (Semana 5) ✅

**Objetivo:** Proveedores LLM con fallback automático de 3 niveles.

| # | Tarea | Archivos | Estado |
|---|---|---|---|
| 5.1 | LLMProvider ABC | `domain/ports/llm_port.py` | ✅ |
| 5.2 | Anthropic provider | `infrastructure/llm/anthropic_provider.py` | ✅ |
| 5.3 | OpenAI provider | `infrastructure/llm/openai_provider.py` | ✅ |
| 5.4 | NVIDIA NIM provider | `infrastructure/llm/nvidia_nim_provider.py` | ✅ |
| 5.5 | HuggingFace provider | `infrastructure/llm/huggingface_provider.py` | ✅ |
| 5.6 | LLM Service (fallback chain) | `infrastructure/llm/llm_service.py` | ✅ |
| 5.7 | Prompts | `infrastructure/llm/prompts.py` | ✅ |
| 5.8 | Tests LLM | `tests/unit/test_llm_service.py`, `test_prompts.py` | ✅ |

---

## F-06: Caché + Resiliencia + Middleware (Semana 6) ✅

**Objetivo:** Caché, rate limiter, error handler centralizado, logging.

| # | Tarea | Archivos | Estado |
|---|---|---|---|
| 6.1 | Caché en memoria | `microservice/cache/response_cache.py` | ✅ |
| 6.2 | Integrar caché en routers | `routers/analisis.py` | ✅ |
| 6.3 | Rate limiter | `middleware/rate_limiter.py` | ✅ |
| 6.4 | Logging middleware | `middleware/logging.py` | ✅ |
| 6.5 | Error handler con FiscalIAError | `middleware/error_handler.py` | ✅ |
| 6.6 | Validación config startup | `config.py` (field validators) | ✅ |
| 6.7 | Tests caché | `tests/unit/test_cache.py`, `test_rate_limiter.py` | ✅ |

---

## F-07: Calidad y Automatización (extra) ✅

| # | Tarea | Archivos | Estado |
|---|---|---|---|
| 7.1 | Ruff linting | `pyproject.toml` | ✅ |
| 7.2 | pytest-html reporte | `pytest.ini` | ✅ |
| 7.3 | Factory-boy fixtures | `tests/factories.py` | ✅ |
| 7.4 | Tests property-based | `tests/unit/test_property_value_objects.py` | ✅ |
| 7.5 | CI workflow | `.github/workflows/ci.yml` | ✅ |
| 7.6 | Pool lifecycle (lifespan) | `microservice/main.py` | ✅ |
| 7.7 | Domain errors + tests | `domain/errors.py`, `tests/unit/test_domain_errors.py` | ✅ |

---

## Resumen de Esfuerzo

| Fase | Descripción | Estado |
|---|---|---|
| F-01 | Fundación Hexagonal | ✅ |
| F-02 | Domain + Persistencia | ✅ |
| F-03 | Endpoints REST | ✅ |
| F-04 | MCP + Background Tasks | ✅ |
| F-05 | LLM Service + Fallback | ✅ |
| F-06 | Caché + Resiliencia | ✅ |
| F-07 | Calidad y Automatización | ✅ |

---

## Herramientas de Calidad

| Herramienta | Propósito |
|---|---|
| **ruff** | Linter + formateador (line-length 120) |
| **pytest-html** | Reporte HTML en `reports/` |
| **factory-boy + Faker** | Datos sintéticos para tests |
| **pytest-asyncio** | Soporte async para tests FastAPI |
| **pytest-cov** | Cobertura con gate ≥ 80% |
| **GitHub Actions** | CI: lint + test + coverage |

---

## Dependencias Externas

| Recurso | Responsable | Estado |
|---|---|---|
| MCP Server con datos Oracle reales | Equipo APEX/Infra | ⏳ |
| PostgreSQL 16+ aprovisionado | Equipo Infra | ⏳ |
| OCI Container Instance | Equipo Infra | ⏳ |
| API Keys LLM reales (Anthropic) | Equipo | ⏳ |

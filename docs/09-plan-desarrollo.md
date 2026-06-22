# Plan de Desarrollo — FiscalIA Microservicio OCI

> **Duración total:** 6 semanas  
> **Metodología:** AI-DLC Hat-Based  
> **Arquitectura:** Hexagonal (Ports & Adapters)

---

## Estado Actual

| Métrica | Valor |
|---|---|
| Fases completadas | F-01 a F-05 ✅ |
| Fase en curso | F-06 (5/7 tareas) |
| Tests unitarios | 66 (incluyendo 9 hypothesis) |
| Tests integración | 5 (todos pasan contra NVIDIA NIM real) |
| Cobertura | 81.93% (quality gate ≥ 80% ✅) |
| Ruff | 0 errores, 0 warnings |
| Commits | 4 en `master` |
| Pendiente externo | Oracle real + PL/SQL bodies (equipo APEX) |
| Pendiente propio | Deploy OCI (documentado) |

---

## F-01: Fundación Hexagonal (Semana 1) ✅

**Objetivo:** Estructura base, conexión Oracle y health endpoint funcional.

| # | Tarea | Archivos | h | Estado |
|---|---|---|---|---|
| 1.1 | Crear `config.py` con variables LLM_* | `microservice/config.py` | 1 | ✅ |
| 1.2 | Pool de conexiones Oracle | `infrastructure/persistence/connection.py` | 2 | ✅ |
| 1.3 | Health endpoint | `api/routers/health.py` | 1 | ✅ |
| 1.4 | FastAPI app factory | `api/main.py` | 1 | ✅ |
| 1.5 | Auth + error handler | `api/middleware/auth.py`, `error_handler.py` | 1 | ✅ |
| 1.6 | Dockerfile + docker-compose | `Dockerfile`, `docker-compose.yml` | 2 | ✅ |
| 1.7 | Tests de health | `tests/unit/test_health.py` | 1 | ✅ |

**Quality Gate:** `docker-compose up` → `/api/v1/health` responde 200 con `oracle_connected: true`.

---

## F-02: Domain + Contrato PL/SQL (Semana 2) ✅

**Objetivo:** Entidades de dominio, VOs, puertos y adapters Oracle.

| # | Tarea | Archivos | h | Estado |
|---|---|---|---|---|
| 2.1 | Value Objects | `domain/value_objects/nit.py`, `periodo.py`, `score_riesgo.py`, `dinero.py` | 2 | ✅ |
| 2.2 | Entities | `domain/entities/contribuyente.py`, `hallazgo.py`, `analisis.py` | 2 | ✅ |
| 2.3 | Ports (interfaces) | `domain/ports/*.py` | 2 | ✅ |
| 2.4 | Adapter: cruces | `infrastructure/adapters/repos/oracle_cruce_repo.py` | 3 | ✅ |
| 2.5 | Adapter: inconsistencias | `infrastructure/adapters/repos/oracle_inconsistencia_repo.py` | 2 | ✅ |
| 2.6 | Adapter: score | `infrastructure/adapters/repos/oracle_score_repo.py` | 2 | ✅ |
| 2.7 | Adapter: guardar análisis | `infrastructure/adapters/repos/oracle_analisis_repo.py` | 2 | ✅ |
| 2.8 | Tests de VOs | `tests/unit/test_value_objects.py` | 2 | ✅ |

**Quality Gate:** Todos los adapters compilan con `oracledb`. VOs pasan tests de validación.

---

## F-03: Use Cases + LiteLLM + DI (Semana 3) ✅

**Objetivo:** Casos de uso orquestando adapters, litellm con fallback y DI.

| # | Tarea | Archivos | h | Estado |
|---|---|---|---|---|
| 3.1 | Use case: analizar contribuyente | `application/use_cases/analizar_contribuyente.py` | 4 | ✅ |
| 3.2 | Use case: calcular score | `application/use_cases/calcular_score.py` | 3 | ✅ |
| 3.3 | DTO | `application/dto/analisis_dto.py` | 1 | ✅ |
| 3.4 | LiteLLM adapter con Router | `infrastructure/adapters/llm/litellm_adapter.py` | 4 | ✅ |
| 3.5 | Prompts | `infrastructure/adapters/llm/prompts.py` | 2 | ✅ |
| 3.6 | Dependency Injection | `api/deps.py` | 1 | ✅ |
| 3.7 | Conectar routers con DI | `api/routers/analisis.py`, `score.py` | 1 | ✅ |
| 3.8 | Tests de use cases con mocks | `tests/unit/test_analisis.py`, `test_score.py` | 4 | ✅ |

**Quality Gate:** `POST /analizar/{nit}` con mocks retorna JSON < 100ms. Cobertura use cases ≥ 80%.

---

## F-04: Pruebas Reales con LLM (Semana 4) ✅

**Objetivo:** Probar pipeline con NVIDIA NIM real (primary + fallback).

| # | Tarea | h | Estado |
|---|---|---|---|
| 4.1 | Configurar cuenta NVIDIA NIM | 1 | ✅ |
| 4.2 | Prueba de integración contra NVIDIA NIM (70B) | 3 | ✅ |
| 4.3 | Prueba de integración contra NVIDIA NIM (3B fallback) | 2 | ✅ |
| 4.4 | Prueba de fallback automático | 2 | ✅ |
| 4.5 | Verificar consumo de tokens | 2 | ✅ |
| 4.6 | Ajustar prompts según respuestas reales | 4 | ✅ |

**Quality Gate:** NVIDIA NIM 70B responde en < 60s. Fallback automático a 3B funciona. Prompts generan JSON válido siempre.

---

## F-05: Cache + Resiliencia + Logging (Semana 5) ✅

**Objetivo:** Producción-ready.

| # | Tarea | Archivos | h | Estado |
|---|---|---|---|---|
| 5.1 | Caché en memoria con TTL | `infrastructure/adapters/cache/memory_cache.py` | 2 | ✅ |
| 5.2 | Integrar caché en use case | `application/use_cases/analizar_contribuyente.py` | 2 | ✅ |
| 5.3 | Retry con tenacity | `infrastructure/adapters/llm/litellm_adapter.py` | 2 | ✅ |
| 5.4 | Fallback degradado (sin IA) | `litellm_adapter.py` | 1 | ✅ |
| 5.5 | Logging estructurado | `api/main.py`, `config.py` | 2 | ✅ |
| 5.6 | Tests de caché | `tests/unit/test_cache.py` | 1 | ✅ |
| 5.7 | Stress test con Locust | `tests/stress/locustfile.py` | 3 | ✅ |

**Quality Gate:** Sin LLM responde < 5s. Caché: segundo llamado < 1s. Stress: 100 usuarios sin errores.

---

## F-06: Documentación + Cierre (Semana 6) ⚠️

**Objetivo:** Cobertura ≥ 80%, documentación completa, listo para OCI.

| # | Tarea | h | Estado |
|---|---|---|---|
| 6.1 | Swagger automático (sin esfuerzo) | 0 | ✅ |
| 6.2 | README completo | 2 | ✅ |
| 6.3 | Documentación de despliegue OCI | 2 | ✅ |
| 6.4 | Pruebas end-to-end | 4 | ⏳ (requiere Oracle real) |
| 6.5 | Verificar cobertura ≥ 80% | 1 | ✅ (81.93%) |
| 6.6 | Documentación AI-DLC actualizada | 2 | ✅ |
| 6.7 | Entrega: repo listo para deploy | 2 | ⏳ (pendiente OCI) |

**Quality Gate:** `pytest --cov=microservice --cov-fail-under=80`. Docs completas.

---

## F-07: Calidad y Automatización (extra) ✅

Mejoras aplicadas fuera del plan original durante la fase de cierre.

| # | Tarea | Archivos | h |
|---|---|---|---|
| 7.1 | Ruff — linting y formato automático | `pyproject.toml` | 1 |
| 7.2 | pytest-html — reporte HTML automático | `pytest.ini` | 0.5 |
| 7.3 | Factory-boy — factories para tests | `tests/factories.py` | 2 |
| 7.4 | Hypothesis — tests property-based | `tests/unit/test_property_value_objects.py` | 2 |
| 7.5 | Conftest mejorado — override_deps + fixtures | `tests/conftest.py` | 1 |
| 7.6 | Docker multi-stage + usuario no-root | `Dockerfile` | 1 |
| 7.7 | GitHub Actions CI workflow | `.github/workflows/ci.yml` | 1 |
| 7.8 | Auth wireado en routers (analizar, score) | `api/routers/analisis.py`, `score.py` | 0.5 |

---

## Resumen de Esfuerzo

| Fase | Horas planeadas | Horas reales | Estado |
|---|---|---|---|
| F-01 | 9 | 9 | ✅ |
| F-02 | 15 | 15 | ✅ |
| F-03 | 16 | 16 | ✅ |
| F-04 | 14 | 14 | ✅ |
| F-05 | 13 | 13 | ✅ |
| F-06 | 11 | 9 | ⚠️ (2h pendientes de infraestructura) |
| F-07 (extra) | — | 9 | ✅ |
| **Total** | **78h** | **85h** | |

---

## Herramientas de Calidad Incorporadas

| Herramienta | Propósito |
|---|---|
| **ruff** | Linter + formateador (rules: E, F, I, N, W, UP) |
| **pytest-html** | Reporte HTML de resultados en `reports/` |
| **factory-boy + Faker** | Datos sintéticos para tests |
| **hypothesis** | Tests property-based para VOs |
| **pytest-asyncio** | Soporte async para tests FastAPI |
| **pytest-cov** | Cobertura con gate ≥ 80% |
| **GitHub Actions** | CI: lint + test + coverage + artifacts |

---

## Dependencias

```
F-01 ──→ F-02 ──→ F-03 ──→ F-04 ──→ F-05 ──→ F-06 ──→ [deploy OCI]
         (necesita  (necesita  (necesita  (necesita  (necesita
          adapters   use cases  LLM real   prod-ready  infra OCI)
          Oracle)    + LLM)
```

**Dependencias externas pendientes:**

| Recurso | Responsable | Estado |
|---|---|---|
| Oracle DB con credenciales reales | Equipo APEX/Infra | ⏳ |
| PL/SQL packages bodies (FISCAL_CROSS, FISCAL_INC, etc.) | Equipo APEX/PL-SQL | ⏳ |
| OCI Container Instance aprovisionada | Equipo Infra | ⏳ |
| APEX REST Data Source configurado | Equipo APEX | ⏳ |
F-01 ──→ F-02 ──→ F-03 ──→ F-04 ──→ F-05 ──→ F-06
         (necesita  (necesita  (necesita  (necesita
          adapters   use cases  LLM real   prod-ready)
          Oracle)    + LLM)
```

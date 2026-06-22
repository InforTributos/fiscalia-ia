# FiscalIA — Microservicio Python OCI

> ![coverage](https://img.shields.io/badge/coverage-81%25-green) ![tests](https://img.shields.io/badge/tests-80-blue) ![python](https://img.shields.io/badge/python-3.11-blue)

Microservicio de IA para fiscalización del Impuesto de Industria y Comercio (ICA) en Valledupar.
Orquesta agentes AGT-01 (CrossCheck) y AGT-03 (InconsistencyAnalyzer) con LLM agnóstico.

## Stack

| Capa | Tecnología |
|---|---|---|
| Framework | FastAPI (Python 3.11+) |
| LLM | Agnóstico vía litellm Router (fallback automático) |
| Base de datos | Oracle 19c+ (python-oracledb, solo PL/SQL) |
| Arquitectura | Hexagonal (Ports & Adapters) |
| Caché | En memoria con TTL configurable |
| Logging | JSON estructurado por request (request_id, tiempo_ms) |
| Calidad | ruff, pytest-cov (≥80%), pytest-html, factory-boy, hypothesis |
| Despliegue | Docker multi-stage / OCI Container Instance |
| CI/CD | GitHub Actions (lint + test + coverage) |
| Metodología | AI-DLC Hat-Based |

## Endpoints

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/v1/health` | Health check + cache_size + uptime |
| POST | `/api/v1/analizar/{nit}` | Análisis completo (cruces + inconsistencias + SRF + explicación IA) |
| POST | `/api/v1/score/{nit}` | Score de Riesgo Fiscal con explicación |
| GET | `/docs` | Swagger/OpenAPI |

## LLM Agnóstico

Configurable vía `.env`. Sin tocar código.

| Proveedor | `LLM_PRIMARY_PROVIDER` | `LLM_PRIMARY_MODEL` |
|---|---|---|
| NVIDIA NIM (free) | `nvidia_nim` | `meta/llama-3.3-70b-instruct` |
| OpenAI | `openai` | `gpt-4o` |
| Anthropic | `anthropic` | `claude-sonnet-4` |
| Gemini | `gemini` | `gemini-2.0-flash` |

**Fallback automático:** si primary falla (timeout, rate-limit, error), Router intenta con `meta/llama-3.2-3b-instruct` (mismo provider NVIDIA). Si falla todo, respuesta degradada sin IA en < 5s.

## Requisitos

- Python 3.11+
- Oracle Database 19c+ con PL/SQL packages (FISCAL_CROSS, FISCAL_INC, FISCAL_SCORE, FISCAL_ANALISIS_IA)
- API Key de NVIDIA NIM (gratis en https://build.nvidia.com)

## Desarrollo local

```bash
pip install -r microservice/requirements.txt
cp .env.example .env
# Editar .env con Oracle y LLM keys
PYTHONPATH=microservice uvicorn api.main:app --reload
```

## Docker

```bash
docker-compose up --build
```

## Tests

```bash
# Unit tests (66 unitarios + 9 hypothesis)
PYTHONPATH=microservice pytest tests/unit/ -v --cov=microservice --cov-report=html:reports/coverage

# Integration tests (requiere API keys reales en .env)
PYTHONPATH=microservice pytest tests/integration/ -v

# Reporte HTML de resultados (se genera automáticamente en reports/)
pytest --cov=microservice --cov-fail-under=80 --html=reports/test-report.html

# Stress test
locust -f tests/stress/locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 -t 2m
```

## Logging

Cada request genera JSON por línea:

```json
{"event": "request_start", "request_id": "e75ee817", "method": "POST", "path": "/api/v1/analizar/9003189639"}
{"event": "request_end", "request_id": "e75ee817", "status": 200, "tiempo_ms": 45230}
```

Campos: `event`, `request_id`, `method`, `path`, `status`, `tiempo_ms`, `error` (si aplica).

## Calidad y Automatización

| Herramienta | Propósito |
|---|---|
| **ruff** | Linter y formateador — `ruff check .` debe pasar limpio |
| **pytest-cov** | Cobertura mínima 80% — gate en CI |
| **pytest-html** | Reporte HTML de resultados en `reports/` |
| **factory-boy + Faker** | Factories reutilizables para tests |
| **hypothesis** | Tests property-based para value objects (NIT, ScoreRiesgo, Dinero) |
| **Locust** | Stress test con 100 usuarios simultáneos |
| **GitHub Actions** | CI automático en cada push: lint → test → coverage |

## Documentación

| Doc | Archivo |
|---|---|
| Arquitectura | `docs/01-arquitectura.md` |
| Modelo de datos | `docs/02-modelo-datos.md` |
| Contrato PL/SQL | `docs/03-contrato-plsql.md` |
| API Endpoints | `docs/04-api-endpoints.md` |
| Configuración | `docs/05-configuracion.md` |
| LLM Config | `docs/06-llm-configuracion.md` |
| Despliegue OCI | `docs/07-despliegue-oci.md` |
| Especificación Agentes | `docs/08-especificacion-agentes.md` |
| Plan de Desarrollo | `docs/09-plan-desarrollo.md` |
| Glosario | `docs/10-glosario.md` |
| Diagramas | `docs/diagrams/arquitectura-hexagonal.puml`, `flujo-analizar.puml` |

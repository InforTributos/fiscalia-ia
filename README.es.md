# FiscalIA — Microservicio Python

> ![tests](https://img.shields.io/badge/tests-116-blue) ![coverage](https://img.shields.io/badge/coverage-72%25-yellow) ![python](https://img.shields.io/badge/python-3.14-blue)

Microservicio de IA para fiscalización del Impuesto de Industria y Comercio (ICA) en Valledupar, con arquitectura hexagonal/DDD y 4 proveedores LLM con fallback automático.

## Stack

| Capa | Tecnología |
|---|---|
| Framework | FastAPI (Python 3.14+) |
| LLM | Agnóstico — Anthropic Claude, OpenAI GPT, NVIDIA NIM, HuggingFace (fallback automático) |
| Base de datos | PostgreSQL 16+ (asyncpg) |
| Arquitectura | Hexagonal (Ports & Adapters) + Domain-Driven Design |
| Caché | En memoria con TTL configurable |
| Errores | Centralizados con jerarquía `FiscalIAError` |
| Calidad | ruff, pytest-cov, pytest-html, factory-boy |

## Endpoints

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/health` | Health check + cache + uptime |
| POST | `/analizar/{nit}` | Análisis completo (verificación documental, cruces, SRF, inconsistencia + explicación IA) |
| POST | `/proceso` | Crear proceso + análisis background asíncrono |
| GET | `/proceso/{proceso_id}` | Estado y resultado del proceso |
| GET | `/status/{nit}` | Estado actual de un NIT |
| GET | `/results/{nit}` | Resultados de análisis |
| GET | `/errors` | Log de errores |
| GET | `/docs` | Swagger/OpenAPI |

## LLM Agnóstico

4 proveedores en 3 tiers con fallback automático vía tenacity:

| Tier | Proveedor | Modelo default |
|---|---|---|
| Tier 1 (pago) | Anthropic/OpenAI | `claude-sonnet-4-20250506` |
| Tier 2 (gratis) | NVIDIA NIM | `qwen/qwen2.5-7b-instruct` |
| Tier 3 (gratis) | HuggingFace | `Qwen/Qwen2.5-7B-Instruct` |

Configurable vía `.env` sin tocar código.

## Requisitos

- Python 3.14+
- PostgreSQL 16+
- API Key de Anthropic, NVIDIA NIM o HuggingFace

## Desarrollo local

```bash
pip install -r requirements.txt
cp .env.example .env
# Editar .env con PostgreSQL y LLM keys
uvicorn main:app --reload
```

## Tests

```bash
# Unit tests
pytest tests/unit/ -v --cov=. --cov-report=html:reports/coverage

# Reporte HTML
pytest --cov=. --cov-fail-under=80 --html=reports/test-report.html || true
```

## Logging

Cada request genera JSON por línea con `request_id` y `tiempo_ms`.

## Calidad

| Herramienta | Propósito |
|---|---|
| **ruff** | Linter y formateador |
| **pytest-cov** | Cobertura objetivo 80% |
| **pytest-html** | Reporte HTML en `reports/` |
| **factory-boy + Faker** | Factories para tests |

## Documentación

| Doc | Archivo |
|---|---|
| Arquitectura | `docs/01-arquitectura.md` |
| Modelo de datos | `docs/02-modelo-datos.md` |
| Contrato MCP | `docs/03-contrato-mcp.md` |
| API Endpoints | `docs/04-api-endpoints.md` |
| Configuración | `docs/05-configuracion.md` |
| LLM Config | `docs/06-llm-configuracion.md` |
| Despliegue OCI | `docs/07-despliegue-oci.md` |
| Especificación Agentes | `docs/08-especificacion-agentes.md` |
| Plan de Desarrollo | `docs/09-plan-desarrollo.md` |
| Glosario | `docs/10-glosario.md` |
| Diagramas | `docs/diagrams/*.puml` |

## Estructura del proyecto

```
fiscalia-ia/
├── domain/
│   ├── ports/           # ABCs: LLMProvider, repositorios
│   ├── services/        # Lógica pura de dominio
│   └── errors.py        # Jerarquía FiscalIAError
├── application/
│   └── use_cases/       # Orquestación (ProcesoOrchestrator)
├── infrastructure/
│   ├── llm/             # Proveedores LLM + prompts
│   ├── persistence/     # asyncpg connection + queries
│   └── mcp/             # Cliente Oracle + pagination + classify
├── middleware/           # Error handler centralizado
├── routers/              # Endpoints FastAPI
├── schemas/              # Pydantic models
├── tests/
│   └── unit/             # 116+ tests
├── docs/                 # Documentación
├── reports/              # Reportes pytest/cov
├── main.py               # Entry point
├── config.py             # Settings con validación
└── .env.example
```

## Licencia

MIT — Ver [LICENSE](LICENSE) para detalles completos.

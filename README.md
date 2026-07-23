# FiscalIA — Microservicio Python

> ![Version](https://img.shields.io/badge/version-2.0.0-blue) ![tests](https://img.shields.io/badge/tests-481-blue) ![coverage](https://img.shields.io/badge/coverage-72%25-yellow) ![python](https://img.shields.io/badge/python-3.14-blue)

Microservicio de inteligencia artificial para **fiscalización del Impuesto de Industria y Comercio (ICA)** en Valledupar, Cesar, Colombia. Arquitectura hexagonal/DDD, con conexión directa a Oracle Database (GENESYS), PostgreSQL, y 4 proveedores LLM con fallback automático.

Desarrollado para la **Secretaría de Hacienda de Valledupar** — sistema Taxation Smart (Oracle APEX 24.x).

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Framework | FastAPI (Python 3.14+) |
| LLM | Agnóstico — Anthropic Claude, OpenAI GPT, NVIDIA NIM, HuggingFace (fallback automático 3 tiers) |
| DB Fiscal | Oracle Database 19c+ (python-oracledb pool async directo) |
| DB Microservicio | PostgreSQL 16+ (asyncpg pool) |
| Arquitectura | Hexagonal (Ports & Adapters) + Domain-Driven Design |
| Caché | En memoria con TTL configurable (3600s default) |
| Errores | Centralizados con jerarquía `FiscalIAError` |
| Calidad | ruff linter, pytest-cov, pytest-html, factory-boy, hypothesis |

## Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Health check + cache + uptime |
| POST | `/analizar/{nit}` | Análisis completo (verificación documental, cruces, SRF, inconsistencia + explicación IA) |
| POST | `/proceso` | Crear proceso de fiscalización + análisis background asíncrono |
| GET | `/proceso/{proceso_id}` | Estado y resultado del proceso |
| GET | `/status/{nit}` | Estado actual de un NIT |
| GET | `/results/{nit}` | Resultados de análisis |
| GET | `/errors` | Log de errores por capa |
| GET | `/docs` | Swagger/OpenAPI |

## LLM Agnóstico

4 proveedores en 3 tiers con fallback automático vía tenacity (backoff factor 2):

| Tier | Proveedor | Modelo default |
|------|-----------|----------------|
| Tier 1 (pago) | Anthropic / OpenAI | `claude-sonnet-4-20250506` / `gpt-4o` |
| Tier 2 (gratis) | NVIDIA NIM | `qwen/qwen2.5-7b-instruct` |
| Tier 3 (gratis) | HuggingFace | `Qwen/Qwen2.5-7B-Instruct` |

Configurable vía `.env` sin tocar código. Discovery automático de modelos disponible.

## Requisitos

- Python 3.14+
- PostgreSQL 16+
- Oracle Database 19c+ (con acceso vía `oracledb`)
- API Keys: Anthropic/OpenAI, NVIDIA NIM o HuggingFace

## Desarrollo local

```bash
pip install -r microservice/requirements.txt
cp .env.example microservice/.env
# Editar .env con credenciales PostgreSQL, Oracle LLM keys
cd microservice
uvicorn main:app --reload
```

> **⚠️ PYTHONPATH:** Todos los comandos pytest requieren `PYTHONPATH=microservice` — el `conftest.py` lo configura automáticamente.

## Tests

```bash
# Unit tests (481 tests)
PYTHONPATH=microservice pytest tests/unit/ -v

# Con cobertura
PYTHONPATH=microservice pytest tests/unit/ --cov=microservice --cov-report=term

# Reporte HTML + coverage gate
PYTHONPATH=microservice pytest tests/unit/ --cov=microservice --cov-fail-under=80 --html=reports/test-report.html
```

| Métrica | Valor |
|---------|-------|
| Tests unitarios | 481 |
| Cobertura | ~72% (sin infra real: PostgreSQL, Oracle, LLM) |
| Linting | ruff 0 errores |

## Reglas Fiscales (R1-R10)

| Regla | Nombre | Fuerza | Estado |
|-------|--------|--------|--------|
| R1 | Retención sin declaración suficiente | DIRECTA | ✅ Operativa |
| R2 | Omiso con presencia registral | DIRECTA | ✅ Operativa |
| **R3** | **Brecha exógena ICA** | **DIRECTA** | **✅ Operativa (fix 2026-07-23)** |
| R4 | Brecha facturación electrónica | DIRECTA | 🟡 Fuente identificada |
| R5 | Contratista estatal no declarante | DIRECTA | 🔴 Pendiente fuente |
| R6 | Declarante en cero persistente | INDICIARIA | ✅ Operativa |
| R7 | CIIU conveniente | MEDIA | ✅ Operativa |
| R8 | Atípico sectorial | INDICIARIA | 🔴 Pendiente diseño |
| R9 | Territorialidad | MEDIA | ✅ Operativa |
| R10 | Caída abrupta de base | INDICIARIA | ✅ Operativa |

Detalle completo en [`docs/08-casuistica-fiscal.md`](docs/08-casuistica-fiscal.md).

## Arquitectura

```
APEX (Oracle) → REST → Microservicio Python (OCI Container Instance)
                            ↓
                Oracle DB (oracledb pool async directo)
                            ↓
                      PostgreSQL (estado procesos + resultados)
                            ↓
                      LLM Service (fallback 3 tiers)
```

Ver [`docs/01-arquitectura.md`](docs/01-arquitectura.md) para el detalle completo.

## Fuentes de Datos Oracle (GENESYS)

| Tabla | Propósito |
|-------|-----------|
| `GI_G_DECLARACIONES` | Declaraciones ICA presentadas al municipio |
| `GI_G_EXOGENA_RETENCIONES` | Exógena municipal de retenciones ICA (RD/RP) |
| `GI_G_INTERMEDIA_DIAN` | Intermediación DIAN — facturación electrónica |
| `TEMP_RQ_DIAN` | Datos DIAN para cruce CIIU/tarifa |
| `SI_C_SUJETOS` + `SI_I_PERSONAS` | Datos del contribuyente |

Ver [`docs/02-modelo-datos.md`](docs/02-modelo-datos.md) — Apéndice A para el detalle completo de tablas Oracle.

## Documentación

| Doc | Archivo |
|-----|---------|
| Arquitectura | [`docs/01-arquitectura.md`](docs/01-arquitectura.md) |
| Modelo de datos | [`docs/02-modelo-datos.md`](docs/02-modelo-datos.md) |
| Contrato Oracle/MCP | [`docs/03-contrato-mcp.md`](docs/03-contrato-mcp.md) |
| API Endpoints | [`docs/04-api-endpoints.md`](docs/04-api-endpoints.md) |
| Configuración | [`docs/05-configuracion.md`](docs/05-configuracion.md) |
| LLM Config | [`docs/06-llm-configuracion.md`](docs/06-llm-configuracion.md) |
| Despliegue OCI | [`docs/07-despliegue-oci.md`](docs/07-despliegue-oci.md) |
| Casuística fiscal (reglas R1-R10) | [`docs/08-casuistica-fiscal.md`](docs/08-casuistica-fiscal.md) |
| Especificación Agentes | [`docs/08-especificacion-agentes.md`](docs/08-especificacion-agentes.md) |
| Anexo técnico | [`docs/08-anexo-tecnico.md`](docs/08-anexo-tecnico.md) |
| Plan de desarrollo | [`docs/09-plan-desarrollo.md`](docs/09-plan-desarrollo.md) |
| Glosario | [`docs/10-glosario.md`](docs/10-glosario.md) |
| Oracle MCP Server | [`docs/11-oracle-mcp-server.md`](docs/11-oracle-mcp-server.md) |
| Manual implementación API | [`docs/manual-implementacion-api.md`](docs/manual-implementacion-api.md) |
| Diagramas | [`docs/diagrams/`](docs/diagrams/) |

### Memoria del proyecto (Obsidian vault)

| Archivo | Propósito |
|---------|-----------|
| [`MEMORY/INDEX.md`](MEMORY/INDEX.md) | Entrada al vault |
| [`MEMORY/TODO.md`](MEMORY/TODO.md) | Deuda técnica y pendientes |
| [`MEMORY/DECISIONS.md`](MEMORY/DECISIONS.md) | Decisiones arquitectónicas |
| [`MEMORY/GOTCHAS.md`](MEMORY/GOTCHAS.md) | Lecciones aprendidas |
| [`MEMORY/CONTEXT.md`](MEMORY/CONTEXT.md) | Contexto del proyecto |

### Agentes

| Archivo | Propósito |
|---------|-----------|
| [`AGENTS.md`](AGENTS.md) | Instrucciones de agentes (fuente de verdad) |
| `.opencode/skills/` | Skills del dominio fiscal, testing, arquitectura hexagonal |
| `.ai-dlc/` | Metodología AI-DLC (config, knowledge, hats, rules) |

## Versión

**v2.0.0** — Ver [`CHANGELOG`](CHANGELOG.md) para historial de versiones.

## Logging

Cada request genera JSON por línea con `request_id` y `tiempo_ms`. Logging estructurado a OCI Logging.

## Metodología

AI-DLC 2026 con Human-in-the-Loop (HITL). 6 unidades secuenciales (U-01 a U-06) con quality gates:
- Cobertura ≥80% (CI)
- No secrets hardcodeados
- OpenAPI habilitado
- Cache TTL configurable
- Retry configurable

Ver [`.ai-dlc/config.yml`](.ai-dlc/config.yml) para la configuración completa.

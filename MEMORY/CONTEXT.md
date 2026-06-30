---
tags: [context, project, config]
---

# Contexto del Proyecto — FiscalIA

---

## Cliente

| Campo | Valor |
|---|---|
| **Entidad** | Alcaldía de Valledupar — Secretaría de Hacienda |
| **Municipio** | Valledupar, Cesar, Colombia |
| **Sistema actual** | Taxation Smart (Oracle APEX 24.x) |
| **Base fiscal** | Oracle Database 19c+ (OCI) |
| **Contacto** | Equipo APEX/Infra |
| **SLA** | 99.5% en horario laboral (6am-10pm) |

## Proveedor

| Campo | Valor |
|---|---|
| **Empresa** | Informática y Tributos S.A.S. |
| **NIT** | 900.318.963-9 |
| **Rol** | Desarrollo y operación del microservicio |

## Arquitectura General

```
APEX (Oracle) → REST → Microservicio Python (OCI Container Instance)
                            ↓
                Oracle MCP Server (HTTP Streamable) → Oracle DB
                            ↓
                      PostgreSQL (estado procesos + resultados)
                            ↓
                      LLM Service (fallback 3 tiers)
```

| Componente | Tecnología |
|---|---|
| Frontend | Oracle APEX 24.x |
| Microservicio | FastAPI (Python 3.14+) en OCI Container Instance |
| DB microservicio | PostgreSQL 16+ (asyncpg) — 6 tablas |
| DB fiscal | Oracle Database (via python-oracledb) |
| LLM Tier 1 | Anthropic Claude / OpenAI GPT (pago) |
| LLM Tier 2 | NVIDIA NIM — Qwen2.5-7B (gratis) |
| LLM Tier 3 | HuggingFace — Qwen2.5-7B (gratis) |
| Comunicacion | python-oracledb directo (pool async), sin MCP |
| Mapas | Google Maps JS API embebida en APEX |

> [!warning] Oracle: python-oracledb directo
> El microservicio usa `oracledb` con pool asincrono para conectar directo a Oracle. Las credenciales van en variables de entorno.

## Variables de Entorno

Definidas en `config.py:Settings` (pydantic-settings). El `.env.example` está en la **raíz del repo**, no en `microservice/`.

### API y PostgreSQL

| Variable | Default | Descripción |
|---|---|---|
| `API_PORT` | `8000` | Puerto del servidor |
| `API_HOST` | `0.0.0.0` | Host del servidor |
| `POSTGRES_HOST` | `localhost` | Host PostgreSQL |
| `POSTGRES_PORT` | `5432` | Puerto PostgreSQL |
| `POSTGRES_DB` | `fiscalia` | Base de datos |
| `POSTGRES_USER` | `fiscalia` | Usuario DB |
| `POSTGRES_PASSWORD` | — | Contraseña DB |

### LLM — Tier 1 (pago)

| Variable | Default | Descripción |
|---|---|---|
| `LLM_TIER1_PROVIDER` | `anthropic` | `anthropic` o `openai` |
| `LLM_TIER1_API_KEY` | — | API key |
| `LLM_TIER1_MODEL` | `claude-sonnet-4-20250506` | Modelo |
| `LLM_TIER1_API_BASE` | `None` (opcional) | Solo para self-hosted |

### LLM — Tier 2 (NVIDIA NIM, gratis)

| Variable | Default | Descripción |
|---|---|---|
| `LLM_TIER2_API_KEY` | — | API key NVIDIA |
| `LLM_TIER2_MODEL` | `qwen/qwen2.5-7b-instruct` | Modelo (minúsculas) |
| `LLM_TIER2_API_BASE` | `https://integrate.api.nvidia.com/v1` | Endpoint |

### LLM — Tier 3 (HuggingFace, gratis)

| Variable | Default | Descripción |
|---|---|---|
| `LLM_TIER3_API_KEY` | — | API key HF |
| `LLM_TIER3_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | Modelo (PascalCase) |
| `LLM_TIER3_API_BASE` | `https://api-inference.huggingface.co/v1` | Endpoint |

### Oracle MCP Server

| Variable | Default | Descripción |
|---|---|---|
| `MCP_SERVER_URL` | — | Endpoint MCP del ADB (`https://dataaccess.adb.{region}.oraclecloudapps.com/adb/mcp/v1/databases/{ocid}`) |
| `MCP_TOKEN_URL` | — | Endpoint OAuth (`https://dataaccess.adb.{region}.oraclecloudapps.com/adb/auth/v1/databases/{ocid}/token`) |
| `MCP_DB_USER` | — | Usuario de base de datos Oracle |
| `MCP_DB_PASSWORD` | — | Contraseña del usuario |
| `MCP_TIMEOUT` | `30` | Timeout por request MCP (seg) |

### Tuning y Pool

| Variable | Default | Descripción |
|---|---|---|
| `LLM_MAX_TOKENS` | `4096` | Tokens máximos por respuesta |
| `LLM_TIMEOUT` | `60` | Timeout por llamada LLM (seg) |
| `CACHE_TTL_SECONDS` | `3600` | TTL caché en memoria (1h) |
| `RETRY_MAX_ATTEMPTS` | `3` | Reintentos fallback LLM |
| `RETRY_BACKOFF_FACTOR` | `2` | Factor backoff exponencial |
| `RETRY_TIMEOUT` | `60` | Timeout total retry (seg) |
| `MAX_CONCURRENT_PROCESSES` | `5` | Tasks simultáneas |
| `PROCESS_TIMEOUT_MINUTES` | `30` | Timeout por proceso |
| `POOL_MIN_SIZE` | `4` | Conexiones mínimas asyncpg |
| `POOL_MAX_SIZE` | `20` | Conexiones máximas asyncpg |
| `POOL_TIMEOUT` | `5` | Timeout adquisición pool (seg) |
| `LOG_LEVEL` | `INFO` | Nivel de logging |

## Modelo de Seguridad

- **Sin API key externa** — APEX accede vía red interna OCI
- **Sin CORS** — solo red privada
- **Autenticación** delegada a APEX
- **Secrets** en OCI Vault (producción) o `.env` (desarrollo)
- **TLS 1.3** obligatorio
- Validación startup: claves placeholder `changeme` lanzan `ValueError`

## Stack Técnico del Microservicio

| Librería | Uso |
|---|---|
| FastAPI | Framework REST |
| asyncpg | Conexión PostgreSQL |
| anthropic, openai, huggingface_hub | LLM providers |
| oracledb | Conexion Oracle async (pool) |
| pydantic + pydantic-settings | Schemas y config |
| tenacity | Retry con backoff |
| ruff | Linter y formateador |
| pytest + pytest-asyncio + pytest-cov | Tests |
| factory-boy + hypothesis | Datos sintéticos |

## Estado actual

| Métrica | Valor |
|---|---|
| Tests | 116 unitarios |
| Cobertura | ~72% (cap sin infra real) |
| Ruff | 0 errores |
| Fases completadas | F-01 a F-07 |

## Metodología AI-DLC

El proyecto usa AI-DLC con HITL (Human in the Loop):

| Aspecto | Detalle |
|---|---|
| **Metodología** | AI-DLC 2026, modo HITL |
| **Unidades** | 6 (U-01 a U-06), secuenciales con dependencias |
| **Hats** | planner, builder, reviewer, test-writer, implementer |
| **Quality Gates** | coverage ≥80%, stress test 50 users p95<90s, no hardcoded secrets, OpenAPI enabled, cache TTL, retry |
| **Commit format** | `{hat}: {unit} - {mensaje}` — ej: `builder: U-03 - implementar endpoint POST /proceso` |

Detalles en `.ai-dlc/config.yml` y `.ai-dlc/knowledge/domain.md` (conocimiento ICA).

## Base de Datos PostgreSQL

Pool asyncpg con `min_size=4, max_size=20, timeout=5`. 6 tablas:

| Tabla | Propósito |
|---|---|
| `clientes` | Contribuyentes registrados |
| `procesos` | Procesos de fiscalización |
| `proceso_intentos` | Intentos de ejecución |
| `proceso_detalle` | Resultados por NIT |
| `proceso_errores` | Errores a nivel proceso |
| `proceso_detalle_errores` | Errores por NIT |

## Despliegue OCI (Producción)

| Aspecto | Configuración |
|---|---|
| CPU | 2 OCPUs |
| Memory | 8 GB |
| Networking | Red privada (sin IP pública) — acceso vía LB interno desde APEX |
| PostgreSQL | Servicio externo en red privada OCI |
| Logging | OCI Logging — JSON structured logs |
| Monitoring | OCI Monitoring + custom metrics |
| Contenedor | Docker en OCI Container Instance |

### Health Check

```
GET /health
Response 200:
{ "status": "healthy", "timestamp": "...", "checks": { "postgres": "ok", "llm_primary": "ok", "llm_fallback1": "ok", "llm_fallback2": "ok" } }
```

### Retención de Datos

| Tabla | Retención |
|---|---|
| `procesos`, `proceso_intentos`, `proceso_detalle` | 2 años |
| `proceso_errores`, `proceso_detalle_errores` | 1 año |
| `clientes` | Indefinido |
| Logs | 6 meses (rotate/archive) |

Implementación: PostgreSQL cron job mensual.

## Costos LLM Estimados

| Tier | Provider | Costo Input | Costo Output | Notas |
|---|---|---|---|---|
| 1 | Anthropic Claude | ~$3/1M tokens | ~$15/1M tokens | Default — mejor calidad |
| 1 | OpenAI GPT-4o | ~$2.50/1M tokens | ~$10/1M tokens | Alternativa más económica |
| 2 | NVIDIA NIM | 5K credits gratis | — | ~2,500-5,000 análisis; 40 RPM |
| 3 | HuggingFace | Mensual gratuito | — | Selecciona provider más rápido |

## Normativa Colombiana Aplicable

- **ICA:** Ley 14 de 1983, Ley 1819 de 2016, Ley 2277 de 2022
- **Facturación electrónica DIAN:** Resolución 000085 de 2022
- **Protección de datos:** Ley 1581 de 2012 (datos tributarios excluidos art. 2.c)
- **Sanción por inexactitud:** Artículo 635 del Estatuto Tributario

## MCP: Paginación

| Parámetro | Default |
|---|---|
| `page_size` | 100 |
| Estrategia | `OFFSET` / `FETCH NEXT` (Oracle 12c+) |
| Transporte | Streamable HTTP con Bearer token |
| Tool principal | `EXECUTE_SQL` (genérica, no custom) |
| Auth | OAuth 2.0 password grant — token fresco por call |

> [!seealso] Referencias
| - [[../docs/01-arquitectura]] — Documentación detallada de arquitectura
| - [[../docs/02-modelo-datos]] — Modelo de datos PostgreSQL
| - [[../docs/03-contrato-mcp]] — Contrato MCP
| - [[../docs/04-api-endpoints]] — Especificación de endpoints
| - [[../.ai-dlc/knowledge/domain]] — Conocimiento ICA (CIIU, SRF, agentes)

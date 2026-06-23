---
tags: [todo, backlog, tech-debt]
---

# TODO — FiscalIA

> [!warning] Los agentes actualizan este archivo
> Al completar una tarea o descubrir nueva deuda técnica, actualizar este archivo.

---

## Pendientes inmediatos

### 🔴 Periodo hardcodeado

| Campo | Valor |
|---|---|
| **Archivo** | `application/use_cases/orquestar_proceso.py` |
| **Problema** | `periodo="2024"` hardcodeado |
| **Fix** | Parametrizar desde `criteria` del proceso |
| **Bloqueado por** | — |
| **Descubierto** | F-04 |

> [!danger] Impacto
> Cualquier cambio de año fiscal requiere modificar código fuente.

### 🟡 TARIFAS_CIIU provisional

| Campo | Valor |
|---|---|
| **Archivo** | `domain/services/crosscheck_service.py` |
| **Problema** | Diccionario `TARIFAS_CIIU` hardcodeado, no refleja valores reales |
| **Fix** | Obtener de Oracle vía MCP o tabla paramétrica en PostgreSQL |
| **Bloqueado por** | MCP Oracle real |
| **Descubierto** | F-02 |

### 🟡 Tests de value objects no contabilizados

| Campo | Valor |
|---|---|
| **Archivos** | `tests/unit/test_value_objects.py`, `test_property_value_objects.py` |
| **Problema** | No se verificó si están incluidos en el conteo de 116 tests |
| **Acción** | Verificar y corregir conteo |
| **Bloqueado por** | — |
| **Descubierto** | Sesión de refactor V2 |

### 🟢 README.md referencia docs desactualizada

| Campo | Valor |
|---|---|
| **Archivo** | `README.md` línea 88 |
| **Problema** | Sigue diciendo "Contrato PL/SQL (Oracle)" |
| **Fix** | Cambiar por "Contrato MCP" apuntando a [[../docs/03-contrato-mcp]] |
| **Bloqueado por** | — |
| **Descubierto** | Sesión de refactor V2 |

---

## Pendientes externos

### MCP Oracle real (conexión HTTP)

| Campo | Valor |
|---|---|
| **Responsable** | Equipo APEX/Infra |
| **Impacto** | Sin esto, MCP adapter es stub, coverage no supera 72% |
| **Qué se necesita** | Oracle MCP Server desplegado + URL endpoint + usuario BD + tablas con datos reales |
| **Estado** | ⏳ Pendiente — adapter ya migrado a HTTP Streamable (listo para conectar) |
| **Nota** | Se requiere `MCP_SERVER_URL`, `MCP_TOKEN_URL`, `MCP_DB_USER`, `MCP_DB_PASSWORD` en `.env` |

### PostgreSQL producción

| Campo | Valor |
|---|---|
| **Responsable** | Equipo Infra OCI |
| **Impacto** | Sin esto, no hay tests de integración reales |
| **Estado** | ⏳ Pendiente |

---

## Backlog (V2+)

- [ ] Parametrizar periodo en `orquestar_proceso.py` → ver [[DECISIONS#Background Tasks: asyncio.create_task]]
- [ ] Implementar Procrastinate para tasks persistentes (actual: `asyncio.create_task`) — En plan pero no implementado
- [ ] Tests de integración con DB real PostgreSQL
- [ ] Tests de integración con MCP real
- [ ] Tests de integración con LLM real
- [ ] Rate limiter con Redis (actual: in-memory)
- [ ] Retención de datos con PostgreSQL cron job
- [ ] AGT-04 LegalDraft: generación automática de actos
- [ ] Parametrizar pesos del SRF vía tabla en PostgreSQL
- [ ] Cache distribuida (Redis) en lugar de in-memory singleton
- [ ] Stress test con locust (50 users, p95 < 90s) — `locustfile.py` existe pero no ejecutado
- [ ] Re-lanzamiento con `cliente_nit` + hash de `criteria` (deep equality) — detectar re-lanzamiento vs proceso nuevo
- [ ] Re-solo NITs fallidos — no soportado en V1 (se re-ejecutan todos)
- [ ] Cancelación de proceso (`DELETE /proceso/{id}`) — no expuesta en V1
- [ ] Procrastinate para cola persistente de background tasks (actual: `asyncio.create_task`)

---

## Quality Gates no verificados

Los siguientes quality gates de `.ai-dlc/config.yml` no se han verificado formalmente:

| Quality Gate | Estado | Notas |
|---|---|---|
| `test_coverage >= 80` | ❌ 72% | Bloqueado por falta de infra real |
| `stress_test: 50 users, p95 < 90s` | ❌ No ejecutado | Requiere OCI o staging |
| `no_hardcoded_secrets` | ✅ Validadores `changeme` en `config.py` | Pasado |
| `openapi_enabled` | ❓ No verificado | Revisar si FastAPI OpenAPI está activo en producción |
| `cache_ttl_seconds: 3600` | ✅ Default en Settings | Pasado |
| `retry_attempts: 3` | ✅ Default en Settings | Pasado |
| `llm_timeout_seconds: 60` | ✅ Default en Settings | Pasado |

> [!tip] Consultar también
> Ver [[DECISIONS]] para entender por qué se tomaron ciertas decisiones técnicas.
> Ver [[GOTCHAS]] para lecciones aprendidas que pueden evitar errores.

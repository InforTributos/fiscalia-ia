---
tags: [todo, backlog, tech-debt]
---

# TODO — FiscalIA

> [!warning] Los agentes actualizan este archivo
> Al completar una tarea o descubrir nueva deuda técnica, actualizar este archivo.

---

## Pendientes inmediatos

### ✅ POST /proceso ya ejecuta descubrimiento y clasificación (RESUELTO)

| Campo | Valor |
|---|---|
| **Archivos** | `tasks/analisis_task.py` (nueva función `pre_filtrar()`) |
| **Fix** | `analizar_proceso()` ahora recibe `criteria`, llama `pre_filtrar()` como Fase 1: conecta Oracle, ejecuta 4 queries de descubrimiento (`obtener_omisos_conocidos`, `obtener_omisos_desconocidos`, `obtener_inexactos_ciiu`, `obtener_inexactos_retenciones`) e inserta candidatos en `proceso_detalle` con clasificación OMISO/INEXACTO. Luego Fase 2 lee `proceso_detalle` y ejecuta el orquestador. Periodo parametrizado desde `criteria`. |
| **Tests** | 5 unitarios (`test_analisis_task.py`) + 3 de integración que cubren: flujo completo mixto, sin candidatos, error parcial en generador. |
| **Resuelto** | 2026-07-09, sesión de worktree |

### 🔴 Cruce con RUES/Confecámaras no implementado (stub vacío)

| Campo | Valor |
|---|---|
| **Archivo** | `infrastructure/mcp/pagination.py` — `obtener_datos_fiscales()` |
| **Problema** | La función retorna siempre `"rues_estado": ""` (hardcodeado, línea ~130). No existe ninguna query, puerto o repositorio que consulte el estado real en RUES/Confecámaras — no hay ni un solo `grep` de una tabla o servicio RUES en toda la base de código. |
| **Impacto en el cálculo del SRF** | En `domain/services/crosscheck_service.py:calcular_srf()`, el componente `estado_rues` (peso 20/100) evalúa `rues == "" or rues is None` → asigna **siempre** `PESO_RUES * 0.5` = 10 puntos fijos a **todos** los contribuyentes, sin importar su estado real. Esto infla artificialmente el SRF de forma pareja y resta precisión al puntaje de riesgo que se le vende al cliente como "objetivo". |
| **Relación con el requerimiento** | `docs/08-especificacion-agentes.md` (AGT-01 CrossCheck) define explícitamente el cruce contra "exógena DIAN, RUES/Confecámaras y padrón ICA" como una de las 3 fuentes obligatorias. Es una de las 4 fuentes/componentes del SRF prometidos, no una función opcional. |
| **Fix** | Definir la fuente de datos RUES (¿tabla Oracle propia, servicio externo de Confecámaras, o archivo de carga manual?) y conectar la consulta real en `obtener_datos_fiscales()`. Requiere definición de negocio: hoy no está claro de dónde saldría ese dato. |
| **Bloqueado por** | Definición de fuente de datos RUES con el cliente/negocio |
| **Descubierto** | 2026-07-08, revisión de fases pendientes contra el requerimiento |
| **Impacto en informe cliente** | El documento `docs/cliente/propuesta-desarrollo-fiscalia.md` (sección 3, paso 2) promete explícitamente el cruce con "su estado en el registro mercantil (RUES)" como parte del flujo — hoy esto no ocurre. |

> [!info] Confirmado: no existe en el esquema real de Oracle
> `docs/changes/002-metodologia-candidatos-ica/design.md` (línea 54, tabla "Mapeo de tablas Oracle") ya documenta esto explícitamente: `| rues | (no tiene equivalente directo — se usa SI_I_PERSONAS para CIIU y estado) |`. Es decir, el equipo ya investigó esto al migrar del esquema genérico al esquema real de Taxation Smart/GENESYS y confirmó que **no hay tabla RUES/Cámara de Comercio en la base Oracle del municipio**. No es que falte conectar una query existente — la fuente de datos externa simplemente no está en esta base de datos y tendría que integrarse desde afuera (API de Confecámaras/RUES, o cargue periódico).
>
> **Proxy interno parcial que sí existe (no es RUES, pero es lo más cercano):** `SI_I_SUJETOS_IMPUESTO.id_sjto_estdo` / `estdo_blqdo` / `fcha_cnclcion` y la tabla catálogo `DF_S_SUJETOS_ESTADO` reflejan el estado del contribuyente **dentro del propio sistema de Hacienda municipal** (activo/bloqueado/cancelado), no su estado en el registro mercantil nacional. Es una señal distinta — un contribuyente puede estar activo en Cámara de Comercio pero bloqueado en el sistema municipal, o viceversa — pero es un dato real ya disponible que hoy no se usa para el componente `estado_rues` del SRF.
>
> **Bug relacionado encontrado:** `infrastructure/mcp/pagination.py:23` (`OBTENER_CONTRIBUYENTE_SQL`) trae `se.cdgo_sjto_estdo AS regimen` — es decir, usa el código de **estado** del sujeto (`DF_S_SUJETOS_ESTADO`) pero lo etiqueta como si fuera el **régimen tributario** (COMUN/SIMPLIFICADO). Son conceptos distintos; parece un error de mapeo/copy-paste. Revisar de dónde debería salir realmente el régimen tributario.

### ✅ Documentación de arquitectura actualizada (RESUELTO)

| Campo | Valor |
|---|---|
| **Archivos afectados** | `docs/01-arquitectura.md`, `docs/03-contrato-mcp.md`, `AGENTS.md` |
| **Fix** | Se actualizaron para reflejar conexión directa `oracledb`. `docs/03-contrato-mcp.md` reescrito completamente: describe `OracleClient` con pool async, queries reales, lookup repository. `AGENTS.md` actualizado: test count 192, periodo parametrizado, MCP Contract describe conexión directa. |
| **Decisión** | Se mantiene `oracledb` directo en producción. No hay servidor MCP gestionado de por medio. |
| **Resuelto** | 2026-07-09 |

### 🟡 Coverage gate de CI (80%) vs. cap real (~72%)

| Campo | Valor |
|---|---|
| **Archivo** | `.github/workflows/ci.yml` |
| **Problema** | El job `test` corre `pytest --cov-fail-under=80`, pero `docs/09-plan-desarrollo.md` y `MEMORY/TODO.md` documentan un cap real de ~72% sin PostgreSQL/MCP/LLM reales. Si esto sigue siendo cierto, el pipeline de CI debería estar fallando en cada push/PR. |
| **Fix** | Verificar el estado real del último run de CI en GitHub Actions. Si sigue en 72%, bajar el gate a un valor alcanzable en CI (ej. 70%) y subir el gate real solo cuando haya tests de integración con infra real. |
| **Bloqueado por** | — |
| **Descubierto** | 2026-07-08, revisión de fases pendientes contra el requerimiento |

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

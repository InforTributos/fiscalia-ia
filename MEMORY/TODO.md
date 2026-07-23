---
tags: [todo, backlog, tech-debt]
---

# TODO — FiscalIA

> [!warning] Los agentes actualizan este archivo
> Al completar una tarea o descubrir nueva deuda técnica, actualizar este archivo.

---

## Pendientes inmediatos

### 🔴 R4 — Facturación electrónica: fuente IDENTIFICADA en Oracle

| Campo | Valor |
|---|---|
| **Archivo** | `application/use_cases/construir_perfil_fiscal.py` (pero la data no se recibe) |
| **Problema** | El motor de reglas (`_evaluar_r4`) existe y está escrito, pero `facturacion_electronica` nunca se setea en el perfil fiscal. |
| **Fuentes identificadas** | `GI_G_INTERMEDIA_DIAN.TTAL_INGRSOS_GRVBLE` (ingresos gravables ICA por contribuyente, por período) y `GI_G_EXOGENA_INGR_FRA_MUNI` (ingresos facturación municipal agregados). |
| **Qué se necesita** | Agregar query a `GI_G_INTERMEDIA_DIAN` (o a la que corresponda) filtrando por NIT y vigencia, y mapear a `facturacion_electronica` en el perfil. |
| **Factible** | Sí — las tablas existen y tienen datos. Solo falta conectar. |

### 🔴 R5 — Contratos públicos (SECOP): fuente de datos no integrada

| Campo | Valor |
|---|---|
| **Archivo** | `application/use_cases/construir_perfil_fiscal.py` (pero la data no se recibe) |
| **Problema** | El motor de reglas (`_evaluar_r5`) existe y está escrito, pero `contratos_publicos` nunca se setea en el perfil fiscal. |
| **Qué se necesita** | Integrar datos de contratación pública (API SECOP, o tabla Oracle si el municipio la replica) y agregar query + mapeo al perfil. |
| **Factible** | Sí — SECOP tiene API pública. O el municipio puede replicar sus contratos en una tabla Oracle. |
| **Bloqueado por** | Decisión técnica sobre la fuente de datos (API SECOP directa vs tabla Oracle replicada) |

### 🔴 R8 — Motor acumulativo sectorial: diseño pendiente

| Campo | Valor |
|---|---|
| **Archivo** | `domain/fiscalizacion/rule_engine.py` (`_evaluar_r8`) |
| **Problema** | R8 necesita percentiles sectoriales por CIIU que se construyen con datos de múltiples contribuyentes. No es una query puntual. |
| **Qué se necesita** | Diseñar un acumulador (en memoria o PostgreSQL) que recolecte bases gravables por CIIU a medida que se analizan contribuyentes y compute percentiles 10/25/50/75/90. |
| **Factible** | Sí — es diseño nuevo, no depende de fuentes externas. Los datos ya se tienen por cada análisis. |
| **Prioridad** | Media — R8 es indiciaria y su precisión mejora con el uso del módulo |

### 🟡 Score de red (score_red) siempre 0

| Campo | Valor |
|---|---|
| **Archivo** | `domain/fiscal/unified_score.py` |
| **Problema** | `resumen_red` nunca se pasa a `calcular_score_unificado()`, por lo que `score_red` es siempre 0. Esto significa que el 15% del peso del score unificado se pierde. |
| **Impacto** | Bajo — no bloqueante, solo resta precisión al score final. Los demás componentes (85%) siguen funcionando. |
| **Fix** | Pasar `resumen_red` desde el caller de `calcular_score_unificado()`.

### ✅ Tests de todos los use cases (RESUELTO)

| Campo | Valor |
|---|---|
| **Archivo** | `tests/unit/test_use_cases.py` |
| **Fix** | 51 tests cubriendo los 7 use cases: `AnalizarComportamientoUseCase` (9), `AnalizarGrafoRiesgoUseCase` (4), `AplicarReglasFiscalesUseCase` (5), `construir_perfil_fiscal_desde_datos_originales` (8), `GenerarExpedienteFiscalUseCase` (2), `GestionarHallazgosUseCase` (14), `RevisarHallazgoAgenteUseCase` (5), `_compactar_hallazgo` (4). Mocking via `AsyncMock` + `@patch` en repos, queries, LLM. Errores cubiertos: `NITNoEncontradoError`, `ProcesoNoEncontradoError`, `HallazgoNoEncontradoError`, `SolicitudInvalidaError`. |
| **Resuelto** | 2026-07-14 |

### ✅ POST /proceso ya ejecuta descubrimiento y clasificación (RESUELTO)

| Campo | Valor |
|---|---|
| **Archivos** | `tasks/analisis_task.py` (nueva función `pre_filtrar()`) |
| **Fix** | `analizar_proceso()` ahora recibe `criteria`, llama `pre_filtrar()` como Fase 1: conecta Oracle, ejecuta 4 queries de descubrimiento (`obtener_omisos_conocidos`, `obtener_omisos_desconocidos`, `obtener_inexactos_ciiu`, `obtener_inexactos_retenciones`) e inserta candidatos en `proceso_detalle` con clasificación OMISO/INEXACTO. Luego Fase 2 lee `proceso_detalle` y ejecuta el orquestador. Periodo parametrizado desde `criteria`. |
| **Tests** | 5 unitarios (`test_analisis_task.py`) + 3 de integración que cubren: flujo completo mixto, sin candidatos, error parcial en generador. |
| **Resuelto** | 2026-07-09, sesión de worktree |

### ✅ Cruce RUES/Confecámaras: resuelto parcialmente (RESUELTO)

| Campo | Valor |
|---|---|
| **Archivo** | `infrastructure/mcp/pagination.py:OBTENER_CONTRIBUYENTE_SQL` |
| **Fix** | Se corrigió el mapeo de `DF_S_SUJETOS_ESTADO` usando CASE (A→ACTIVO, I→INACTIVO, O→OMISO_DESCONOCIDO). Ya no es `""` hardcodeado. Se replicó en `behavioral.py:CONTRIBUYENTE_LOOKUP_SQL`. El SRF ahora recibe `rues_estado` real del sistema municipal (no es RUES/Confecámaras, pero es el proxy más cercano disponible). |
| **Pendiente** | Si el negocio requiere el estado RUES real (Cámara de Comercio), se necesita integración externa (API Confecámaras o carga periódica). El dato de `DF_S_SUJETOS_ESTADO` es el estado dentro del sistema de Hacienda municipal, no el registro mercantil nacional. |
| **Resuelto** | 2026-07-23 |

### ✅ TARIFAS_CIIU carga desde Oracle (RESUELTO)

| Campo | Valor |
|---|---|
| **Archivo** | `domain/services/crosscheck_service.py`, `infrastructure/mcp/pagination.py` |
| **Fix** | Se implementó `cargar_tarifas_desde_oracle()` que carga las tarifas más frecuentes por CIIU desde `GI_G_DECLARACIONES_DETALLE` (atributos 2107/4371/4874) al startup del servicio. Fallback a `TARIFAS_CIIU_DEFAULT` si Oracle no responde. |
| **Resuelto** | 2026-07-23 |

### ✅ R9 — Territorialidad (RESUELTO)

| Campo | Valor |
|---|---|
| **Archivo** | `application/use_cases/construir_perfil_fiscal.py` |
| **Fix** | Se agregó cómputo de `ingresos_locales_no_declarados = max(total_exógena - total_declarado, 0)`. Sin queries nuevas. R9 ahora es operativa. |
| **Resuelto** | 2026-07-23 |

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

### ✅ R3 — Corregido VLOR_BSE en vez de VLOR_RTNCION (RESUELTO)

| Campo | Valor |
|---|---|
| **Archivos** | `infrastructure/mcp/behavioral.py`, `infrastructure/mcp/pagination.py` |
| **Problema** | R3 comparaba `SUM(vlor_rtncion)` (retención, ej: $40k) vs `BSE_GRVBLE` (base declarada, ej: $100M). Las magnitudes eran inconmensurables — R3 nunca disparaba. |
| **Fix** | Cambiar a `SUM(vlor_bse)` (base de operación, ej: $8M) y filtrar solo `cdgo_exgna_tpo_rgstro = 'RD'` (retenciones recibidas). |
| **Bug adicional** | `pagination.py` usaba `'RECIBIDA'`/`'PRACTICADA'` en CASE WHEN — valores reales son `'RD'`/`'RP'`. Columnas siempre daban 0. |
| **Tests** | `tests/unit/test_exogena_fix.py` — 13 tests (6 SQL structure + 7 domain behavior) |
| **Resuelto** | 2026-07-23 |

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

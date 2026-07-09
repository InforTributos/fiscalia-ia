---
tags: [decisions, architecture]
---

# Decisiones Técnicas — FiscalIA

> [!info] Formato
> Cada entrada documenta una decisión importante, las alternativas evaluadas y el fundamento.

---

## 1. Arquitectura Hexagonal (Ports & Adapters) + DDD

| Campo | Valor |
|---|---|
| **Fecha** | F-01 (Semana 1) |
| **Estado** | ✅ Implementado |
| **Ámbito** | Todo el microservicio |

**Decisión:** Separar el dominio puro (`domain/`) de la infraestructura (`infrastructure/`) usando ABCs como puertos.

**Alternativas evaluadas:**
- Monolito flat (V1) — rechazado por acoplamiento entre capas
- Clean Architecture — similar pero más estricta, optamos por hexagonal por simplicidad

**Razón:** El dominio no debe depender de frameworks ni bases de datos. Los puertos permiten mockear repositorios fácilmente en tests.

> [!seealso] Consecuencias
> Ver [[GOTCHAS#Importación de repos en routers]] para un efecto secundario de esta decisión.

---

## 2. LLM: Provider Agnostic Custom (sin litellm)

| Campo | Valor |
|---|---|
| **Fecha** | F-05 |
| **Estado** | ✅ Implementado |
| **Ámbito** | `infrastructure/llm/` |

**Decisión:** Implementación propia con 4 providers directos y fallback chain con tenacity.

**Alternativas evaluadas:**
- litellm — descartado por overhead y dependencia externa
- LangChain — sobre-ingeniería para este caso

**Razón:** Control total sobre fallback chain, sin dependencia de librería externa que cambie su API.

---

## 3. Background Tasks: asyncio.create_task (sin cola)

| Campo | Valor |
|---|---|
| **Fecha** | F-04 |
| **Estado** | ✅ Implementado |
| **Ámbito** | `tasks/analisis_task.py` |

**Decisión:** Usar `asyncio.create_task` en lugar de Procrastinate/Celery.

**Alternativas evaluadas:**
- Procrastinate (basado en PostgreSQL) — rechazado por simplicidad en V1
- Celery + Redis — sobre-ingeniería

**Limitación confirmada:** Las tasks se pierden si el contenedor cae. Mitigación: el estado del proceso se persiste en PostgreSQL, se puede re-lanzar.

> [!warning] Deuda técnica
> Migrar a Procrastinate cuando se necesiten guarantees. Ver [[TODO]].

---

## 4. Pool PostgreSQL: asyncpg con FastAPI lifespan

| Campo | Valor |
|---|---|
| **Fecha** | F-01 |
| **Estado** | ✅ Implementado |

**Decisión:** Pool asyncpg gestionado vía FastAPI lifespan (`main.py`).

**Razón:** El pool debe crearse al iniciar y cerrarse al detener. FastAPI lifespan garantiza ambas operaciones.

**Configuración por defecto:** `min_size=4, max_size=20, timeout=5s`

> [!tip] Configurable
> Pool configurable via `POOL_MIN_SIZE`, `POOL_MAX_SIZE`, `POOL_TIMEOUT` en `.env`.

---

## 5. Errores: Jerarquía FiscalIAError (sin HTTPException)

| Campo | Valor |
|---|---|
| **Fecha** | F-01 |
| **Estado** | ✅ Implementado |

**Decisión:** Todos los errores del dominio heredan de `FiscalIAError`. El middleware `error_handler.py` los mapea a HTTP.

**Alternativa evaluada:**
- HTTPException directo en routers — rechazado porque acopla el dominio a FastAPI

**Razón:** Los routers nunca lanzan `HTTPException`. El dominio es puro y reutilizable.

> [!seealso] Detalles
| Ver [[GOTCHAS#PYTHONPATH]] para más contexto sobre errores comunes.

---

## 6. Repositorios: instanciados a module level (sin DI)

| Campo | Valor |
|---|---|
| **Fecha** | F-03 |
| **Estado** | ✅ Implementado |

**Decisión:** Los routers instancian `PostgresProcesoRepo()` directamente, sin framework de inyección de dependencias.

**Alternativa evaluada:**
- DI con FastAPI `Depends` — rechazado por simplicidad, la app es pequeña

**Razón:** Menos boilerplate. Para tests, los repos se mockean vía fixtures.

---

## 7. Caché: en memoria (sin Redis)

| Campo | Valor |
|---|---|
| **Fecha** | F-06 |
| **Estado** | ✅ Implementado |

**Decisión:** `MemoryCache` singleton con TTL configurable (3600s default).

**Alternativa evaluada:**
- Redis — rechazado por ser una dependencia adicional en V1

**Limitación:** La caché se pierde al reiniciar el contenedor. Aceptable para V1.

---

## 8. Control de versiones: Git (no DB de prompts)

| Campo | Valor |
|---|---|
| **Fecha** | F-05 |
| **Estado** | ✅ Implementado |

**Decisión:** Los prompts se versionan en Git como archivos `.py` con constantes string.

**Alternativa evaluada:**
- DB de prompts con versionado — rechazado por complejidad en V1
- Archivos YAML/JSON — prefirieron Python por consistencia con el código

**Limitación:** No hay A/B testing en V1.

---

## 9. Commits: Formato AI-DLC con hats

| Campo | Valor |
|---|---|
| **Fecha** | F-01 |
| **Estado** | ✅ Implementado |

**Decisión:** Formato `{hat}: {unit} - {mensaje}` — ej: `builder: U-03 - implementar endpoint POST /proceso`.

**Razón:** Trazabilidad entre cambios de código y unidades del plan AI-DLC. Los hats (builder, reviewer, planner, test-writer, implementer) indican qué rol generó el cambio.

---

## 10. Metodología: AI-DLC con HITL

| Campo | Valor |
|---|---|
| **Fecha** | F-01 |
| **Estado** | ✅ Implementado |

**Decisión:** Usar AI-DLC 2026 en modo Human-in-the-Loop, con 6 unidades (U-01 a U-06) secuenciales.

**Razón:** Metodología diseñada para proyectos IA donde el agente produce y el humano revisa/valida (HITL). Las unidades tienen dependencias claras y quality gates medibles.

**Quality gates definidos:**
- `test_coverage >= 80`
- `stress_test: 50 users, p95 < 90s`
- `no_hardcoded_secrets`: true
- `openapi_enabled`: true
- `cache_ttl_seconds`: 3600
- `retry_attempts`: 3
- `llm_timeout_seconds`: 60

---

## 11. Config: pydantic-settings con extra: ignore

| Campo | Valor |
|---|---|
| **Fecha** | F-01 |
| **Estado** | ✅ Implementado |

**Decisión:** `Settings` singleton a module level, `model_config = {"env_file": ".env", "extra": "ignore"}`.

**Razón:** Singleton evita re-leer `.env` en cada import. `extra: ignore` tolera variables de entorno del sistema que no están en el modelo. Validadores rechazan placeholders `changeme`.

---

## 12. Nivel de Riesgo SRF: 3 bandas

| Campo | Valor |
|---|---|
| **Fecha** | F-02 |
| **Estado** | ✅ Implementado |
| **Archivo** | `domain/services/inconsistency_service.py` |

**Decisión:** Score 0-100, umbrales: BAJO (<40), MEDIO (40-70), ALTO (>70).

**Razón:** Simplicidad operativa. Coincide con criterios típicos de fiscalización municipal.

---

## 13. Modelo LLM: Qwen2.5-7B para Tiers 2 y 3

| Campo | Valor |
|---|---|
| **Fecha** | F-05 |
| **Estado** | ✅ Implementado |

**Decisión:** Usar Qwen2.5-7B-Instruct como modelo gratuito común para NVIDIA NIM (Tier 2) y HuggingFace (Tier 3).

**Alternativas evaluadas:**
- Llama-3.1-8B — descartado por peor performance en instruction following multilingüe (IFEval 60.68 vs 74.87)
- Otros modelos gratuitos de 7B — Qwen2.5 tiene mejor soporte JSON nativo

**Benchmarks vs Llama-3.1-8B:**
| Benchmark | Qwen2.5-7B | Llama-3.1-8B |
|---|---|---|
| IFEval multilingual | **74.87** | 60.68 (+23%) |
| JSON output | Optimizado | Base |
| Idiomas | 29+ (incl. español) | 8 |
| Contexto | 128K tokens | 128K |
| Tamaño | 7B params | 8B |

**Casing:** NVIDIA NIM requiere `qwen/qwen2.5-7b-instruct` (minúsculas), HuggingFace requiere `Qwen/Qwen2.5-7B-Instruct` (PascalCase). Ver [[GOTCHAS#Model Qwen: casing importa]].

---

## 14. Re-lanzamiento de procesos: criteria hash

| Campo | Valor |
|---|---|
| **Fecha** | F-03 |
| **Estado** | ✅ Implementado — `routers/proceso.py:crear_proceso()` + `queries.obtener_proceso_por_criteria()` (actualizado 2026-07-08, esta entrada estaba desactualizada) |

**Decisión:** Mismo `cliente_id` + mismos `criteria` → nuevo intento con `numero_intento` incremental.

**Comportamiento implementado:**
- Proceso `EN_PROCESO`/`EN_COLA`/`PREFILTRANDO`/`PENDIENTE` con mismos criteria → rechazar con 409 `ProcesoEnProcesoError`
- Proceso `COMPLETADO`/`ERROR`/`INTERRUMPIDO` → nuevo intento incremental (`numero_intento = intentos_total + 1`)
- Re-solo NITs fallidos → **no soportado en V1**
- Resultados anteriores se preservan (historial de intentos)

> [!warning] No es hash — es comparación de texto JSON
> La comparación real es `criteria::text = $2::text` (`infrastructure/persistence/queries.py:48`), es decir texto JSON serializado, no un hash canónico. Si `json.dumps(criteria)` produce el mismo dict con distinto orden de keys, la comparación de texto podría no detectar que son "los mismos criterios". Riesgo bajo en la práctica porque `criteria` se construye siempre con el mismo orden de keys en `crear_proceso()`, pero es una fragilidad a tener presente si se refactoriza ese diccionario.

# Arquitectura del Microservicio — FiscalIA

## 1. Estilo Arquitectónico

**Hexagonal (Ports & Adapters) + Domain-Driven Design**.

### Principios

- El dominio es puro: **no depende de nada externo** (ni PostgreSQL, ni LLM, ni FastAPI)
- Las interfaces (puertos) se definen en `domain/ports/` como ABCs
- Los adaptadores concretos (PostgreSQL, Anthropic, FastAPI) implementan esas interfaces
- Los casos de uso en `application/use_cases/` orquestan el flujo inyectando dependencias por constructor
- Los errores de dominio se modelan en `domain/errors.py` — cada tipo tiene un código HTTP asociado

---

## 2. Diagrama de Capas

```
┌──────────────────────────────────────────────────────────────────┐
│                     INBOUND ADAPTERS                              │
│                                                                  │
│  routers/           (FastAPI, HTTP/REST)                         │
│    ├── analisis.py      → POST /analizar/{nit}                  │
│    ├── proceso.py       → POST /proceso, POST /proceso/{id}/cancelar│
│    ├── status.py        → GET /proceso/{id}/status              │
│    ├── results.py       → GET /proceso/{id}/results             │
│    ├── errors.py        → GET /proceso/{id}/errors              │
│    ├── health.py        → GET /health                           │
│    ├── entidad.py       → POST/GET entidad endpoints            │
│    ├── behavioral.py    → GET comportamiento, grafo-riesgo,     │
│    │                       expediente-fiscal, ranking-          │
│    │                       comportamental, visor-grafo          │
│    ├── fiscalizacion.py → reglas, hallazgos, revision           │
│    └── export.py        → GET /proceso/{id}/export              │
│  schemas/            (Pydantic request/response)                 │
│  middleware/         (Error Handler centralizado)                │
│  main.py             (App factory)                               │
└──────────────────────────┬───────────────────────────────────────┘
                           │  llaman a Use Cases
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     APPLICATION                                   │
│                                                                  │
│  application/use_cases/                                          │
│    └── orquestar_proceso.py   (ProcesoOrchestrator)              │
│                                                                  │
│  Orquesta: recibe repos + LLM por DI, llama al dominio y luego   │
│  persiste resultados.                                            │
└──────────────────────────┬───────────────────────────────────────┘
                           │  depende de interfaces (ports)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     DOMAIN                                        │
│                                                                  │
│  domain/ports/              (ABCs: LLMProvider, repositorios)    │
│    ├── llm_port.py          → LLMProvider                        │
│    ├── contribuyente_repo.py → ContribuyenteRepo                 │
│    └── proceso_repo.py      → ProcesoRepo                        │
│  domain/services/           (Lógica pura, sin IO)                │
│    ├── crosscheck_service.py → SRF 4 componentes, clasificación  │
│    └── inconsistency_service.py → nivel_riesgo()                 │
│  domain/errors.py           → Jerarquía FiscalIAError            │
│                                                                  │
│  CERO dependencias externas. Solo Python estándar + typing.      │
└──────────────────────────┬───────────────────────────────────────┘
                           │  implementado por adapters
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     OUTBOUND ADAPTERS                              │
│                                                                  │
│  infrastructure/llm/                                             │
│    ├── anthropic_provider.py   → Anthropic Claude                │
│    ├── openai_provider.py      → OpenAI GPT                      │
│    ├── nvidia_nim_provider.py  → NVIDIA NIM (Qwen)               │
│    ├── huggingface_provider.py → HuggingFace (Qwen)              │
│    ├── llm_service.py          → Fallback chain con tenacity     │
│    └── prompts.py              → 4 prompts de análisis           │
│  infrastructure/persistence/                                     │
│    ├── connection.py    → asyncpg connection pool                │
│    └── queries.py       → SQL queries (postgres)                 │
│  infrastructure/mcp/                                             │
│    ├── oracle_adapter.py → Cliente MCP Oracle                    │
│    ├── client_adapter.py → Adapter para client MCP               │
│    ├── pagination.py     → Paginación de resultados MCP          │
│    └── classify.py       → Clasificación CIIU                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Flujo de una Solicitud

### Flujo POST /proceso (proceso batch)

```
Cliente
    │ POST /proceso (criteria, periodo)
    ▼
middleware/rate_limiter.py  → 10 req/min/IP
    │
    ▼
middleware/error_handler.py  → captura cualquier FiscalIAError
    │
    ▼
routers/proceso.py
    │ Valida criterios, crea proceso (PENDIENTE)
    ▼
tasks/analisis_task.py  → pre_filtrar()
    │ 1. Estado → PREFILTRANDO
    │ 2. 4 descubrimientos vía Oracle directo:
    │    - obtener_omisos_conocidos
    │    - obtener_omisos_desconocidos
    │    - obtener_inexactos_ciiu
    │    - obtener_inexactos_retenciones
    │ 3. Clasifica cada NIT (OMISO / INEXACTO)
    │ 4. Estado → PREFILTRADO_COMPLETADO
    ▼
tasks/analisis_task.py  → analizar_nits()
    │ Para cada NIT en paralelo (vía asyncio.gather):
    │   1. Estado → EN_PROCESO
    │   2. Llama a obtener_datos_fiscales()
    │      desde pagination.py (Oracle directo, 4 generators)
    │   3. Clasifica, extrae inconsistencias, calcula SRF
    │   4. Invoca LLM vía llm.analyze() (fallback chain)
    │   5. Persiste resultado vía repositorio_proceso
    │   6. Cachea resultado
    │ Estado → COMPLETADO (o ERROR si todos fallan)
    │
    ▼
Cliente (JSON: proceso_id, estado, resumen)
```

### POST /analizar/{nit} (análisis individual)

```
Cliente
    │ POST /analizar/{contribuyente_nit}?periodo=2024
    ▼
middleware/error_handler.py  → captura cualquier FiscalIAError
    │
    ▼
routers/analisis.py
    │ 1. Verifica caché → miss
    │ 2. Crea OracleClient()
    │ 3. Llama a obtener_datos_fiscales(client, nit, periodo)
    │    DIRECTAMENTE desde pagination.py
    │ 4. Si no hay datos → NITNoEncontradoError
    │ 5. Clasifica (clasificar_por_datos)
    │ 6. Extrae inconsistencias (extraer_inconsistencias)
    │ 7. Calcula SRF (calcular_srf)
    │ 8. Construye prompt según clasificación
    │ 9. Invoca LLM vía llm.analyze(messages)
    │    (NO llm_service.generate)
    │ 10. Cachea y retorna AnalyzeResponse
    ▼
infrastructure/llm/llm_service.py  → LLMService.analyze()
    │ Fallback chain: Tier1 → Tier2 → Tier3 (tenacity)
    │ Retorna dict con explicacion, tokens, provider
    ▼
Cliente (JSON: AnalyzeResponse)
```

---

## 4. Inyección de Dependencias

Sin DI framework. `routers/analisis.py` y `proceso.py` instancian dependencias directamente:

| Dependencia | Implementación concreta |
|---|---|
| Cache | `MemoryCache` (singleton) |
| LLM | `LLMService` (fallback 3 tiers) |
| ContribuyenteRepo | `queries.obtener_contribuyente` |
| ProcesoRepo | `queries` (crear/obtener/actualizar) |
| Oracle Client | `OracleClient` (oracledb pool async directo) |

Si mañana se cambia PostgreSQL por Oracle, se cambia `infrastructure/persistence/queries.py` sin tocar dominio.

---

## 5. Manejo de Errores

Todos los errores de dominio heredan de `FiscalIAError` (abstracto):

| Error | HTTP | Uso |
|---|---|---|
| `NITNoEncontradoError` | 404 | NIT no encontrado en el padrón |
| `ProcesoNoEncontradoError` | 404 | proceso_id inválido |
| `EntidadNoEncontradoError` | 404 | entidad fiscalizadora no registrada |
| `HallazgoNoEncontradoError` | 404 | hallazgo fiscal no encontrado |
| `ProcesoEnProcesoError` | 409 | proceso ya en ejecución |
| `MCPConnectionError` | 503 | MCP Oracle no disponible |
| `MCPTimeoutError` | 504 | tiempo de espera agotado en MCP |
| `MCPConnectionRefusedError` | 503 | conexión rechazada por MCP Oracle |
| `MCPPageError` | 500 | error de paginación en MCP |
| `OracleQueryFailError` | 500 | error en consulta Oracle |
| `OracleTimeoutError` | 504 | tiempo de espera agotado en Oracle |
| `LLMUnavailableError` | 503 | servicio de IA no disponible |
| `LLMTimeoutError` | 504 | tiempo de espera agotado en LLM |
| `LLMRateLimitError` | 429 | límite de tasa excedido en LLM |
| `LLMInvalidJSONError` | 500 | respuesta JSON inválida del LLM |
| `LLMAllProvidersFailedError` | 503 | todos los proveedores LLM fallaron |
| `PGConnError` | 503 | error de conexión a PostgreSQL |
| `PGInsertFailError` | 500 | error al insertar en PostgreSQL |
| `CriteriosInvalidosError` | 422 | criterios de búsqueda inválidos |
| `WorkerTimeoutError` | 504 | tiempo de espera del worker agotado |
| `OrchestrationFailError` | 500 | error de orquestación del proceso |
| `ConfiguracionInvalidaError` | 500 | configuración inválida (`.env`) |
| `SolicitudInvalidaError` | 422 | solicitud mal formada |
| `LookupError` | 500 | error de resolución de entidad |

El handler en `middleware/error_handler.py` captura todas y retorna JSON estandarizado:
```json
{"error": "NIT_NO_ENCONTRADO", "mensaje": "...", "request_id": "abc123"}
```

---

## 6. Árbol del Proyecto

```
fiscalia-ia/
├── domain/
│   ├── __init__.py
│   ├── errors.py
│   ├── ports/
│   │   ├── __init__.py
│   │   ├── contribuyente_repo.py
│   │   ├── llm_port.py
│   │   ├── lookup_repository.py
│   │   └── proceso_repo.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── crosscheck_service.py
│   │   └── inconsistency_service.py
│   ├── behavioral/
│   │   ├── __init__.py
│   │   ├── behavioral_score.py
│   │   ├── indicators.py
│   │   ├── peer_group.py
│   │   └── seasonal.py
│   ├── fiscal/
│   │   ├── __init__.py
│   │   ├── unified_score.py
│   │   └── dossier.py
│   ├── fiscalizacion/
│   │   ├── __init__.py
│   │   ├── agent_reviewer.py
│   │   ├── legal_window.py
│   │   ├── rule_engine.py
│   │   ├── rules_catalog.py
│   │   └── scoring.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── taxpayer_graph.py
│   │   └── network_score.py
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── contribuyente.py
│   │   ├── analisis.py
│   │   └── hallazgo.py
│   └── value_objects/
│       ├── __init__.py
│       ├── nit.py
│       ├── periodo.py
│       ├── dinero.py
│       └── score_riesgo.py
├── application/
│   ├── __init__.py
│   ├── dto/
│   │   └── __init__.py
│   └── use_cases/
│       ├── __init__.py
│       ├── analizar_comportamiento.py
│       ├── analizar_grafo_riesgo.py
│       ├── aplicar_reglas_fiscales.py
│       ├── construir_perfil_fiscal.py
│       ├── generar_expediente_fiscal.py
│       ├── gestionar_hallazgos.py
│       ├── orquestar_proceso.py
│       └── revisar_hallazgo_agente.py
├── infrastructure/
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── anthropic_provider.py
│   │   ├── huggingface_provider.py
│   │   ├── llm_service.py
│   │   ├── nvidia_nim_provider.py
│   │   ├── openai_provider.py
│   │   └── prompts.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── behavioral.py
│   │   ├── classify.py
│   │   ├── client_adapter.py
│   │   ├── graph.py
│   │   ├── oracle_adapter.py
│   │   └── pagination.py
│   └── persistence/
│       ├── __init__.py
│       ├── connection.py
│       ├── hallazgos_queries.py
│       ├── queries.py
│       ├── repositorio_contribuyente.py
│       ├── repositorio_lookup.py
│       └── repositorio_proceso.py
├── middleware/
│   ├── __init__.py
│   ├── error_handler.py
│   ├── logging.py
│   └── rate_limiter.py
├── routers/
│   ├── __init__.py
│   ├── analisis.py
│   ├── behavioral.py
│   ├── entidad.py
│   ├── errors.py
│   ├── export.py
│   ├── fiscalizacion.py
│   ├── health.py
│   ├── proceso.py
│   ├── results.py
│   └── status.py
├── schemas/
│   ├── __init__.py
│   ├── behavioral.py
│   ├── contribuyente.py
│   ├── errors.py
│   ├── fiscalizacion.py
│   ├── proceso.py
│   ├── results.py
│   └── status.py
├── cache/
│   ├── __init__.py
│   └── response_cache.py
├── tasks/
│   ├── __init__.py
│   ├── analisis_task.py
│   ├── concurrency.py
│   └── retry.py
├── presentation/
│   ├── __init__.py
│   └── graph_viewer.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── factories.py
│   ├── unit/
│   ├── integration/
│   ├── functional/
│   ├── e2e/
│   └── stress/
├── main.py
├── config.py
└── .env.example
```

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
│    ├── analisis.py   → POST /analizar/{nit}                     │
│    ├── proceso.py    → POST /proceso, GET /proceso/{id}         │
│    ├── status.py     → GET /status/{nit}                        │
│    ├── results.py    → GET /results/{nit}                       │
│    ├── errors.py     → GET /errors                              │
│    └── health.py     → GET /health                              │
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

### POST /analizar/{nit}

```
Cliente
    │ POST /analizar/{nit}
    ▼
middleware/error_handler.py  → captura cualquier FiscalIAError
    │
    ▼
routers/analisis.py
    │ Valida NIT, invoca orquestador
    │ Pasa cache, repos, llm_service por DI
    ▼
application/use_cases/orquestar_proceso.py
    │ 1. Verifica caché → miss
    │ 2. Llama a contribuyente_repo.obtener_contribuyente(nit)
    │ 3. Llama a mcp para:
    │    - cruces documentales
    │    - inconsistencias
    │    - SRF (4 componentes)
    │ 4. Construye contexto → llama a llm_service.generate()
    ▼
infrastructure/llm/llm_service.py
    │ Fallback chain: Tier1 → Tier2 → Tier3 (tenacity)
    │ Retorna JSON estructurado o respuesta degradada
    ▼
orquestar_proceso.py
    │ 5. Persiste resultado vía proceso_repo
    │ 6. Guarda en caché
    │ 7. Retorna AnalyzeResponse
    ▼
middleware/error_handler.py  → log + request_id
    │
    ▼
Cliente (JSON)
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
| MCP Client | `OracleMCPAdapter` |

Si mañana se cambia PostgreSQL por Oracle, se cambia `infrastructure/persistence/queries.py` sin tocar dominio.

---

## 5. Manejo de Errores

Todos los errores de dominio heredan de `FiscalIAError` (abstracto):

| Error | HTTP | Uso |
|---|---|---|
| `NITNoEncontradoError` | 404 | NIT no existe en ORACLE_MINI |
| `ProcesoNoEncontradoError` | 404 | proceso_id inválido |
| `ClienteNoEncontradoError` | 404 | NIT no encontrado en MCP |
| `ProcesoEnProcesoError` | 409 | proceso ya en ejecución |
| `MCPConnectionError` | 503 | MCP Oracle no disponible |
| `LLMUnavailableError` | 503 | Todos los LLM fallaron |
| `ConfiguracionInvalidaError` | 500 | `.env` inválido |

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
│   │   ├── contribuyente_repo.py
│   │   ├── llm_port.py
│   │   └── proceso_repo.py
│   └── services/
│       ├── crosscheck_service.py
│       └── inconsistency_service.py
├── application/
│   └── use_cases/
│       └── orquestar_proceso.py
├── infrastructure/
│   ├── llm/
│   │   ├── anthropic_provider.py
│   │   ├── huggingface_provider.py
│   │   ├── llm_service.py
│   │   ├── nvidia_nim_provider.py
│   │   ├── openai_provider.py
│   │   └── prompts.py
│   ├── mcp/
│   │   ├── oracle_adapter.py
│   │   ├── client_adapter.py
│   │   ├── pagination.py
│   │   └── classify.py
│   └── persistence/
│       ├── connection.py
│       └── queries.py
├── middleware/
│   └── error_handler.py
├── routers/
│   ├── analisis.py
│   ├── proceso.py
│   ├── status.py
│   ├── results.py
│   ├── errors.py
│   └── health.py
├── schemas/
│   ├── responses.py
│   └── requests.py
├── tests/
│   └── unit/
│       ├── test_*.py
├── main.py
├── config.py
└── .env.example
```

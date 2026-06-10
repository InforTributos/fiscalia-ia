# Arquitectura del Microservicio — FiscalIA

## 1. Estilo Arquitectónico

**Hexagonal (Ports & Adapters)** — también conocido como _Arquitectura de Puertos y Adaptadores_.

### Principios

- El dominio es puro: **no depende de nada externo** (ni Oracle, ni litellm, ni FastAPI)
- Las interfaces (puertos) se definen en el dominio
- Los adapters concretos (Oracle, litellm, FastAPI) implementan esas interfaces
- Los casos de uso orquestan el flujo inyectando dependencias por constructor

---

## 2. Diagrama de Capas

```
┌──────────────────────────────────────────────────────────────────┐
│                     INBOUND ADAPTERS                              │
│                                                                  │
│  api/routers/     (FastAPI, HTTP/REST)                           │
│  api/schemas/     (Pydantic para request/response)               │
│  api/middleware/  (Auth, Error Handler, Logging)                │
│  api/deps.py      (Dependency Injection)                         │
│  api/main.py      (App factory)                                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │  llaman a Use Cases
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     APPLICATION                                   │
│                                                                  │
│  application/use_cases/   (AnalizarContribuyente, CalcularScore) │
│  application/dto/         (Data Transfer Objects)                │
│                                                                  │
│  Orquesta: recibe puertos por DI, llama al dominio y adapters    │
└──────────────────────────┬───────────────────────────────────────┘
                           │  depende de interfaces (ports)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     DOMAIN                                        │
│                                                                  │
│  domain/entities/        (Contribuyente, Hallazgo, Analisis)     │
│  domain/value_objects/   (NIT, Periodo, ScoreRiesgo, Dinero)     │
│  domain/ports/           (CruceRepo, InconsistenciaRepo,         │
│                           ScoreRepo, AnalisisRepo, LLMPort)      │
│                                                                  │
│  CERO dependencias externas. Solo Python estándar.               │
└──────────────────────────┬───────────────────────────────────────┘
                           │  implementado por adapters
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     OUTBOUND ADAPTERS                              │
│                                                                  │
│  infrastructure/adapters/repos/   (Oracle PL/SQL via python-     │
│                                    oracledb)                     │
│ infrastructure/adapters/llm/     (litellm Router + prompts)     │
│  infrastructure/adapters/cache/   (MemoryCache)                   │
│  infrastructure/persistence/      (Pool de conexiones Oracle)    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Flujo de una Solicitud

### POST /api/v1/analizar/{nit}

```
Cliente (APEX)
    │ POST /analizar/{nit}?periodo=2025-01
    │ Header: X-API-Key
    ▼
api/middleware/logging.py
    │ Genera request_id (UUID)
    │ Loggea request_start (method, path, query)
    ▼
api/routers/analisis.py
    │ Valida API Key (middleware auth)
    │ Obtiene use case por DI (api/deps.py)
    ▼
application/use_cases/analizar_contribuyente.py
    │ Crea NIT y Periodo (value objects)
    │ llama a cruce_repo.obtener_cruces(nit, periodo)
    ▼
infrastructure/adapters/repos/oracle_cruce_repo.py
    │ callfunc FISCAL_CROSS.obtener_cruces()
    ▼
Oracle Database
    │ Ejecuta PL/SQL, devuelve cursor
    ▼
oracle_cruce_repo.py  →  list[dict]
    │
    ▼
analizar_contribuyente.py
    │ llama a inconsistencia_repo.obtener_inconsistencias()
    ▼
oracle_inconsistencia_repo.py  →  list[dict]
    │
    ▼
analizar_contribuyente.py
    │ llama a score_repo.obtener_srf()
    ▼
oracle_score_repo.py  →  dict
    │
    ▼
analizar_contribuyente.py
    │ Verifica caché: ¿respuesta ya almacenada?
    ├── Cache hit → salta LLM, usa respuesta almacenada
    └── Cache miss → construye contexto → llama a llm.analizar(contexto)
                       ▼
infrastructure/adapters/llm/litellm_adapter.py
    │ litellm.Router.acompletion() → primary o fallback
    │ tenacity retry (3 intentos, backoff 2x)
    ▼
NVIDIA NIM (Llama 3.3 70B) / NVIDIA NIM (Llama 3.2 3B)
    │ Responde con JSON estructurado
    ▼
analizar_contribuyente.py
    │ Guarda resultado en caché (cache.guardar)
    │ Mapea hallazgos a entidades de dominio
    │ Guarda en Oracle vía analisis_repo.guardar_analisis()
    ▼
oracle_analisis_repo.py  →  FISCAL_ANALISIS_IA
    │
    ▼
analizar_contribuyente.py  →  AnalisisDTO
    │
    ▼
api/routers/analisis.py  →  JSON Response
    │
    ▼
APEX (cliente)
```

---

## 4. Inyección de Dependencias

```
api/deps.py
    ├── get_cache()                → MemoryCache (singleton)
    ├── get_cruce_repo()           → OracleCruceRepo
    ├── get_inconsistencia_repo()  → OracleInconsistenciaRepo
    ├── get_score_repo()           → OracleScoreRepo
    ├── get_analisis_repo()        → OracleAnalisisRepo
    ├── get_llm()                  → LiteLLMAdapter
    │
    ├── get_analizar_use_case(repos + llm + cache)   → AnalizarContribuyente
    └── get_calcular_score_use_case(repo + llm + cache) → CalcularScore
```

Cada use case recibe solo las interfaces que necesita, nunca instancias concretas. Si mañana se cambia Oracle por PostgreSQL, se crea `PostgresCruceRepo` que implemente `CruceRepo` y se cambia solo `deps.py`.

---

## 5. Árbol del Proyecto (solo microservicio)

```
microservice/
├── api/                              ← Inbound adapters
│   ├── main.py                       ← FastAPI app
│   ├── deps.py                       ← DI wiring
│   ├── routers/
│   │   ├── analisis.py               ← POST /analizar/{nit}
│   │   ├── score.py                  ← POST /score/{nit}
│   │   └── health.py                 ← GET /health
│   ├── schemas/
│   │   ├── analisis.py               ← Pydantic request/response
│   │   ├── score.py
│   │   └── contribuyente.py
│   └── middleware/
│       ├── auth.py                   ← API Key validation
│       └── error_handler.py          ← Exception handlers
│
├── domain/                           ← Core (0 dependencias)
│   ├── entities/
│   │   ├── contribuyente.py
│   │   ├── hallazgo.py
│   │   └── analisis.py
│   ├── value_objects/
│   │   ├── nit.py
│   │   ├── periodo.py
│   │   ├── score_riesgo.py
│   │   └── dinero.py
│   └── ports/
│       ├── contribuyente_repo.py
│       ├── cruce_repo.py
│       ├── inconsistencia_repo.py
│       ├── analisis_repo.py
│       └── llm_port.py
│
├── application/                       ← Casos de uso
│   ├── use_cases/
│   │   ├── analizar_contribuyente.py
│   │   └── calcular_score.py
│   └── dto/
│       └── analisis_dto.py
│
├── infrastructure/                    ← Outbound adapters
│   ├── adapters/
│   │   ├── repos/
│   │   │   ├── oracle_cruce_repo.py
│   │   │   ├── oracle_inconsistencia_repo.py
│   │   │   ├── oracle_score_repo.py
│   │   │   └── oracle_analisis_repo.py
│   │   ├── llm/
│   │   │   ├── litellm_adapter.py
│   │   │   └── prompts.py
│   │   └── cache/
│   │       └── memory_cache.py
│   └── persistence/
│       └── connection.py              ← Pool Oracle
│
├── config.py                          ← Settings (desde .env)
└── requirements.txt
```

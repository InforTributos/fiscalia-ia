# Manual de Implementación — FiscalIA API

> **Versión:** 2.0.0  
> **Última actualización:** Julio 2026  
> **Arquitectura:** Hexagonal (Ports & Adapters) + DDD  
> **Stack:** Python 3.12+ / FastAPI / asyncpg / PostgreSQL 16+

---

## Tabla de Contenidos

1. [Descripción General](#1-descripción-general)
2. [Arquitectura](#2-arquitectura)
3. [Prerrequisitos](#3-prerrequisitos)
4. [Instalación Local](#4-instalación-local)
5. [Configuración de Variables de Entorno](#5-configuración-de-variables-de-entorno)
6. [Base de Datos PostgreSQL](#6-base-de-datos-postgresql)
7. [API Endpoints](#7-api-endpoints)
8. [Ejemplos de Uso](#8-ejemplos-de-uso)
9. [Sistema de Fallback LLM](#9-sistema-de-fallback-llm)
10. [Despliegue en OCI](#10-despliegue-en-oci)
11. [Monitoreo y Alarmas](#11-monitoreo-y-alarmas)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Descripción General

FiscalIA es un microservicio de IA para la fiscalización del ICA (Impuesto de Industria, Comercio y Oficios Varios) en Valledupar, Colombia. Orquesta agentes de IA para:

- **Pre-filtrado masivo:** Obtención y clasificación de contribuyentes vía Oracle Database directo (oracledb)
- **Análisis individual/batch:** Evaluación fiscal con LLM (fallback de 3 niveles)
- **Detección de hallazgos:** Motor de reglas fiscales (R01-R10) con fuerza probatoria
- **Análisis comportamental:** Detección de patrones anómalos entre contribuyentes
- **Gestión de expedientes:** Ciclo de vida completo de hallazgos fiscales (DETECTADO → CONFIRMADO)

**Modelo de seguridad:** Solo red privada OCI. APEX es el único consumidor vía red interna.

---

## 2. Arquitectura

### 2.1. Diagrama de Capas

```mermaid
flowchart TB
    subgraph INBOUND["🔌 INBOUND ADAPTERS"]
        direction TB
        R["routers/<br/>FastAPI HTTP/REST"]
        S["schemas/<br/>Pydantic request/response"]
        M["middleware/<br/>Error Handler · Rate Limiter · Logging"]
        MA["main.py<br/>App factory + lifespan"]
    end

    subgraph APP["⚙️ APPLICATION"]
        direction TB
        U1["orquestar_proceso.py<br/>Análisis batch/individual"]
        U2["analizar_comportamiento.py<br/>Análisis comportamental"]
        U3["analizar_grafo_riesgo.py<br/>Grafo de riesgo"]
        U4["generar_expediente_fiscal.py<br/>Expediente consolidado"]
        U5["aplicar_reglas_fiscales.py<br/>Motor R01-R10"]
        U6["gestionar_hallazgos.py<br/>CRUD hallazgos"]
        U7["revisar_hallazgo_agente.py<br/>Revisión IA de hallazgos"]
        U8["construir_perfil_fiscal.py<br/>Perfil desde Oracle"]
    end

    subgraph DOMAIN["🧠 DOMAIN"]
        direction TB
        P["domain/ports/<br/>ABCs: LLMProvider, repositorios"]
        DS["domain/services/<br/>Lógica pura: SRF, inconsistencias"]
        B["domain/behavioral/<br/>Score comportamental, indicadores"]
        F["domain/fiscal/<br/>Score unificado, expediente"]
        FI["domain/fiscalizacion/<br/>Reglas R01-R10, scoring"]
        G["domain/graph/<br/>Grafo de riesgo empresarial"]
        E["domain/errors.py<br/>FiscalIAError hierarchy"]
        NOTE["CERO dependencias externas"]
    end

    subgraph OUTBOUND["🗄️ OUTBOUND ADAPTERS"]
        direction TB
        LLM["infrastructure/llm/<br/>4 providers + fallback chain"]
        PG["infrastructure/persistence/<br/>asyncpg pool + queries + hallazgos"]
        MCP["infrastructure/mcp/<br/>Oracle Client (oracledb direct) + behavioral + graph"]
    end

    INBOUND -->|"llaman a Use Cases"| APP
    APP -->|"depende de ports"| DOMAIN
    DOMAIN -->|"implementado por adapters"| OUTBOUND

    style INBOUND fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style APP fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style DOMAIN fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style OUTBOUND fill:#fce4ec,stroke:#c62828,stroke-width:2px
```

### 2.2. Árbol del Proyecto

```mermaid
mindmap
  root((fiscalia-ia))
    domain
      errors.py
      ports
        contribuyente_repo.py
        llm_port.py
        lookup_repository.py
        proceso_repo.py
      services
        crosscheck_service.py
        inconsistency_service.py
      behavioral
        behavioral_score.py
        indicators.py
        peer_group.py
        seasonal.py
      fiscal
        unified_score.py
        dossier.py
      fiscalizacion
        agent_reviewer.py
        legal_window.py
        rule_engine.py
        rules_catalog.py
        scoring.py
      graph
        models.py
        taxpayer_graph.py
        network_score.py
      entities
        contribuyente.py
        analisis.py
        hallazgo.py
      value_objects
        nit.py
        periodo.py
        dinero.py
        score_riesgo.py
    application
      use_cases
        orquestar_proceso.py
        analizar_comportamiento.py
        analizar_grafo_riesgo.py
        generar_expediente_fiscal.py
        aplicar_reglas_fiscales.py
        gestionar_hallazgos.py
        revisar_hallazgo_agente.py
    infrastructure
      llm
        anthropic_provider.py
        openai_provider.py
        nvidia_nim_provider.py
        huggingface_provider.py
        llm_service.py
        prompts.py
      persistence
        connection.py
        queries.py
        hallazgos_queries.py
        repositorio_proceso.py
        repositorio_contribuyente.py
        repositorio_lookup.py
      mcp
        oracle_adapter.py
        pagination.py
        classify.py
        behavioral.py
        graph.py
    middleware
      error_handler.py
      logging.py
      rate_limiter.py
    routers
      health.py
      proceso.py
      status.py
      results.py
      errors.py
      analisis.py
      entidad.py
      behavioral.py
      fiscalizacion.py
      export.py
    schemas
    cache
    tasks
      analisis_task.py
      concurrency.py
      retry.py
    presentation
      graph_viewer.py
    tests
```

---

## 3. Prerrequisitos

| Requisito | Versión mínima | Notas |
|---|---|---|
| Python | 3.12+ | Recomendado: 3.12 |
| PostgreSQL | 16+ | asyncpg pool asíncrono |
| pip | 24+ | Gestor de paquetes |
| Git | 2.x | Control de versiones |
| Docker | 24+ (opcional) | Para despliegue |
| Oracle Client | oracledb | Conexión directa a Oracle 19c+ |

### API Keys necesarias

| Servicio | Tier | Obligatorio | Registro |
|---|---|---|---|
| Anthropic | Tier 1 (pago) | Sí (mínimo 1 tier) | console.anthropic.com |
| OpenAI | Tier 1 (pago) | Alternativa a Anthropic | platform.openai.com |
| NVIDIA NIM | Tier 2 (gratis) | No (fallback) | developer.nvidia.com |
| HuggingFace | Tier 3 (gratis) | No (fallback) | huggingface.co |

---

## 4. Instalación Local

### 4.1. Clonar el repositorio

```bash
git clone <repo-url> fiscalia-ia
cd fiscalia-ia
```

### 4.2. Crear entorno virtual

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 4.3. Instalar dependencias

```bash
pip install -r microservice/requirements.txt
```

### 4.4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus valores reales (ver §5)
```

### 4.5. Verificar instalación

```bash
# Linting
ruff check microservice/ tests/

# Tests unitarios
PYTHONPATH=microservice pytest tests/unit/ -v

# Cobertura
PYTHONPATH=microservice pytest tests/unit/ --cov=microservice --cov-report=term
```

### 4.6. Ejecutar el servidor

```bash
# Desde la raíz del proyecto
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

El servidor estará disponible en:
- **API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 5. Configuración de Variables de Entorno

### 5.1. Variables Obligatorias

```env
# === PostgreSQL ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fiscalia
POSTGRES_USER=fiscalia
POSTGRES_PASSWORD=tu_password_real

# === LLM Tier 1 (mínimo 1 proveedor) ===
LLM_TIER1_PROVIDER=anthropic
LLM_TIER1_API_KEY=sk-ant-...
LLM_TIER1_MODEL=claude-sonnet-4-20250506
```

### 5.2. Variables Opcionales (con defaults)

```env
# === API ===
API_PORT=8000
API_HOST=0.0.0.0

# === Municipio ===
MUNICIPIO=Valledupar
DEPARTAMENTO=Cesar

# === Cache ===
CACHE_TTL_SECONDS=3600    # 1 hora

# === Retry / Timeouts ===
LLM_TIMEOUT=0             # 0 = sin limite
RETRY_MAX_ATTEMPTS=1
RETRY_BACKOFF_FACTOR=2
RETRY_TIMEOUT=0

# === Performance ===
NIT_CONCURRENCY=5
BATCH_DB_SIZE=50

# === Pool PostgreSQL ===
POOL_MIN_SIZE=4
POOL_MAX_SIZE=20
POOL_TIMEOUT=5

# === Background Tasks ===
MAX_CONCURRENT_PROCESSES=5
PROCESS_TIMEOUT_MINUTES=0

# === Oracle Database ===
ORACLE_HOST=138.121.200.30
ORACLE_PORT=1521
ORACLE_SERVICE=ORCLPDB
ORACLE_USER=FISCALIA_APP
ORACLE_PASSWORD=changeme
ORACLE_POOL_MIN=2
ORACLE_POOL_MAX=5
ORACLE_POOL_TIMEOUT=30

# === Log ===
LOG_LEVEL=INFO
```

### 5.3. Validación al Startup

`config.py` valida automáticamente que ninguna API key ni contraseña tenga el valor `"changeme"`. Si se detecta, lanza `ConfiguracionInvalidaError` con el nombre de la variable ofensiva.

**Nunca** comitear el archivo `.env` al repositorio (está en `.gitignore`).

### 5.4. Configuración por Ambiente

| Ambiente | `LOG_LEVEL` | `CACHE_TTL` | `MAX_CONCURRENT_PROCESSES` |
|---|---|---|---|
| Desarrollo | `DEBUG` | `60` (1 min) | `2` |
| Pruebas | `INFO` | `300` (5 min) | `5` |
| Producción | `INFO` | `3600` (1 hr) | `5` |

---

## 6. Base de Datos PostgreSQL

### 6.1. Tablas del Sistema

| Tabla | Propósito | Granularidad |
|-------|-----------|-------------|
| `entidades_fiscalizadoras` | Consumidores de la API | 1 fila por entidad |
| `procesos` | Cada criterio de fiscalización | 1 fila por proceso |
| `proceso_intentos` | Cada ejecución/re-lanzamiento | 1 fila por intento |
| `proceso_detalle` | NITs analizados por IA | 1 fila por NIT por intento |
| `proceso_errores` | Errores a nivel de proceso | 1 fila por error |
| `proceso_detalle_errores` | Errores por NIT | 1 fila por error |
| `hallazgos_fiscales` | Hallazgos detectados (R01-R10) | 1 fila por hallazgo |

### 6.2. Diagrama ER

```mermaid
erDiagram
    entidades_fiscalizadoras ||--o{ procesos : "lanza"
    entidades_fiscalizadoras ||--o{ hallazgos_fiscales : "genera"
    procesos ||--o{ proceso_intentos : "tiene"
    procesos ||--o{ proceso_detalle : "detalla"
    procesos ||--o{ hallazgos_fiscales : "produce"
    proceso_intentos ||--o{ proceso_errores : "registra"
    proceso_detalle ||--o{ proceso_detalle_errores : "puede tener"
```

### 6.3. Ejecutar Migraciones

```bash
# Conectar a PostgreSQL y ejecutar DDL
psql -h localhost -U fiscalia -d fiscalia -f db/migrations/001_create_tables.sql
```

### 6.4. Política de Retención

| Tabla | Retención | Acción |
|-------|-----------|--------|
| `procesos`, `proceso_intentos`, `proceso_detalle` | 2 años | DELETE en cascada |
| `proceso_errores`, `proceso_detalle_errores` | 1 año | DELETE |
| `entidades_fiscalizadoras` | Indefinido | Nunca se eliminan |

---

## 7. API Endpoints

**Base URL:** `http://localhost:8000/api/v1`

### 7.1. Health Check

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servicio |

**Response (200):**
```json
{
  "status": "healthy",
  "database": "connected",
  "oracle": "connected",
  "version": "2.0.0"
}
```

**Flujo del health check:**

```mermaid
flowchart LR
    A["GET /health"] --> B["Verificar pool<br/>PostgreSQL"]
    A --> C["Verificar pool<br/>Oracle"]
    B --> D{"¿Conectado?"}
    C --> E{"¿Conectado?"}
    D -->|"Sí"| F["database: connected"]
    D -->|"No"| G["database: disconnected"]
    E -->|"Sí"| H["oracle: connected"]
    E -->|"No"| I["oracle: disconnected"]
    F --> J["Retornar status"]
    G --> J
    H --> J
    I --> J

    style A fill:#e3f2fd,stroke:#1565c0
    style F fill:#c8e6c9,stroke:#2e7d32
    style G fill:#ffcdd2,stroke:#c62828
    style H fill:#c8e6c9,stroke:#2e7d32
    style I fill:#ffcdd2,stroke:#c62828
```

---

### 7.2. Entidades Fiscalizadoras

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/entidad_fiscalizadora` | Crear entidad |
| `GET` | `/entidad_fiscalizadora/{nit}` | Obtener entidad por NIT |
| `GET` | `/entidades_fiscalizadoras` | Listar entidades (paginado) |

**POST /entidad_fiscalizadora — Request:**
```json
{
  "entidad_nit": "9003189639",
  "nombre": "Municipio de Valledupar",
  "email": "fiscalizacion@valledupar.gov.co"
}
```

**Response (201):**
```json
{
  "id": "uuid-de-la-entidad",
  "entidad_nit": "9003189639",
  "nombre": "Municipio de Valledupar",
  "email": "fiscalizacion@valledupar.gov.co",
  "activo": true
}
```

---

### 7.3. Procesos de Fiscalización

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/proceso` | Crear proceso asíncrono |
| `GET` | `/proceso/{id}/status` | Consultar estado |
| `GET` | `/proceso/{id}/results` | Consultar resultados (paginado) |
| `GET` | `/proceso/{id}/errors` | Consultar errores |
| `GET` | `/proceso/{id}/export` | Exportar a XLSX |

#### POST /proceso — Crear proceso asíncrono

**Request:**
```json
{
  "entidad_nit": "9003189639",
  "nombre": "Proceso Comercio Q1 2024",
  "vigencia_ini": "2024-01-01",
  "vigencia_fin": "2024-12-31",
  "tipo_regimen": "COMUN",
  "actividades_economicas": ["4711", "4712", "4721"],
  "periodo": "2024",
  "tipo": "COMPLETO",
  "max_nits": 0,
  "umbral_retenciones_pct": 5.0
}
```

| Parámetro | Tipo | Default | Requerido | Descripción |
|---|---|---|---|---|
| `entidad_nit` | string | — | Sí | NIT de la entidad fiscalizadora |
| `nombre` | string | — | Sí | Nombre descriptivo del proceso |
| `vigencia_ini` | string | — | Sí | Fecha inicial del período (YYYY-MM-DD) |
| `vigencia_fin` | string | — | Sí | Fecha final del período (YYYY-MM-DD) |
| `tipo_regimen` | string | — | Sí | COMUN / SIMPLIFICADO |
| `actividades_economicas` | string[] | — | Sí | Lista de códigos CIIU |
| `periodo` | string | — | Sí | Año fiscal |
| `tipo` | string | `BASICO` | No | `BASICO` = SRF+LLM (paralelo), `COMPLETO` = BASICO + comportamiento + reglas + score + resumen |
| `max_nits` | int | 0 | No | Límite de NITs a procesar (0 = ilimitado) |
| `umbral_retenciones_pct` | float | 5.0 | No | Umbral porcentual para inexactos retenciones |

**Response (201):**
```json
{
  "proceso_id": "uuid-del-proceso",
  "intento_id": 1,
  "estado": "EN_COLA",
  "nombre": "Proceso Comercio Q1 2024",
  "entidad_nit": "9003189639",
  "resumen": {
    "total_nits": 0,
    "omisos": 0,
    "exactos": 0,
    "inexactos": 0
  },
  "proceso_analisis": {
    "estado": "EN_COLA",
    "mensaje": "Proceso creado. Iniciando pre-filtrado de candidatos en Oracle."
  },
  "created_at": "2026-06-21T10:30:00Z"
}
```

**Cancelación:** Endpoint `POST /proceso/{proceso_id}/cancelar` disponible. Marca el proceso como `INTERRUMPIDO` y cancela la tarea activa via `asyncio.CancelledError`.

**Re-lanzamiento:**
| Situación | Comportamiento |
|-----------|---------------|
| Proceso `EN_PROCESO` con mismos criteria | HTTP 409 `PROCESO_EN_PROCESO` |
| Proceso `COMPLETADO`/`ERROR` con mismos criteria | Nuevo intento con `numero_intento` incremental |
| Resultados anteriores | Se preservan (historial) |

**Flujo interno de POST /proceso:**

```mermaid
sequenceDiagram
    participant Client as Cliente (APEX)
    participant API as FastAPI
    participant Oracle as Oracle Database
    participant PG as PostgreSQL
    participant LLM as LLM Service

    Client->>API: POST /proceso (criterios)
    API->>PG: INSERT proceso (PENDIENTE)
    API->>PG: INSERT proceso_intentos (EN_PROCESO)
    API->>Oracle: 4 queries descubrimiento
    loop Paginación Oracle
        Oracle-->>API: página de NITs
        API->>PG: INSERT proceso_detalle
    end
    API->>API: Clasificar: omisos / exactos / inexactos
    API->>PG: UPDATE proceso_detalle (clasificación)
    API->>PG: UPDATE proceso_intentos (PREFILTRADO_COMPLETADO)
    API-->>Client: 201 + resumen
    Note over API,LLM: Background task
    API->>Oracle: obtener_datos_fiscales(nit)
    Oracle-->>API: datos fiscales
    API->>LLM: analizar(datos + contexto)
    LLM->>LLM: Tier 1 → Tier 2 → Tier 3 (fallback)
    LLM-->>API: hallazgos + explicación
    API->>PG: UPDATE proceso_detalle (hallazgos + SRF)
    API->>PG: UPDATE proceso_intentos (procesados +1)
    API->>PG: UPDATE proceso_intentos (COMPLETADO)
```

#### GET /proceso/{id}/status — Consultar estado

**Response (200):**
```json
{
  "proceso_id": "uuid-o-id-12345",
  "estado": "EN_PROCESO",
  "entidad_nit": "9003189639",
  "intento_actual": {
    "numero": 2,
    "estado": "EN_PROCESO",
    "procesados": 995,
    "errores": 3
  },
  "progreso": {
    "porcentaje": 45.2,
    "total_nits": 2200,
    "procesados": 995,
    "faltantes": 1205
  },
  "clasificacion": {
    "omisos": { "total": 1200, "procesados": 600 },
    "inexactos": { "total": 1000, "procesados": 395 }
  }
}
```

**Estados posibles:**

| Estado | Significado |
|--------|-------------|
| `PENDIENTE` | Proceso creado, esperando ejecución |
| `PREFILTRANDO` | MCP está obteniendo NITs |
| `PREFILTRADO_COMPLETADO` | NITs clasificados, análisis IA en cola |
| `EN_COLA` | Esperando worker disponible |
| `EN_PROCESO` | Análisis IA en ejecución |
| `COMPLETADO` | Todos los NITs analizados |
| `INTERRUMPIDO` | Contenedor reiniciado mid-process (recuperable) |
| `ERROR` | Error en el proceso |

**Máquina de estados:**

```mermaid
stateDiagram-v2
    [*] --> PENDIENTE: POST /proceso
    PENDIENTE --> PREFILTRANDO: Inicia MCP
    PREFILTRANDO --> PREFILTRADO_COMPLETADO: MCP completa
    PREFILTRANDO --> ERROR: MCP falla
    PREFILTRADO_COMPLETADO --> EN_COLA: Background task encolada
    EN_COLA --> EN_PROCESO: Worker disponible
    EN_PROCESO --> COMPLETADO: Todos los NITs OK
    EN_PROCESO --> ERROR: Timeout / Error fatal
    EN_PROCESO --> INTERRUMPIDO: Contenedor cae
    INTERRUMPIDO --> EN_COLA: Re-lanzamiento manual
    ERROR --> [*]
    COMPLETADO --> [*]
```

#### GET /proceso/{id}/results — Consultar resultados

**Query parameters:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `page` | int | 1 | Número de página |
| `page_size` | int | 50 | Registros por página (max 500) |
| `intento_id` | int | null | Filtrar por intento específico |
| `include_partial` | boolean | false | Retornar resultados parciales |
| `clasificacion` | string | null | `OMISO`, `EXACTO`, `INEXACTO` |
| `min_score` | float | null | Score mínimo del MCP |
| `ordenar_por` | string | `mcp_score` | Campo de ordenamiento |
| `direccion` | string | `desc` | `asc` o `desc` |

**Response (200):**
```json
{
  "proceso_id": "uuid-o-id-12345",
  "estado": "COMPLETADO",
  "intento_id": 2,
  "paginacion": {
    "page": 1,
    "page_size": 50,
    "total_registros": 2200,
    "total_paginas": 44
  },
  "resultados": [
    {
      "contribuyente_nit": "9003189639",
      "razon_social": "COMERCIO XYZ S.A.S.",
      "ciiu": "4711",
      "clasificacion": "INEXACTO",
      "mcp_score": 85.5,
      "mcp_razon": "Diferencia de ingresos del 45%",
      "srf_total": 78,
      "nivel_riesgo": "ALTO",
      "hallazgos": [
        {
          "tipo": "SUBDECLARACION_EXOGENA",
          "declarado_ica": 50000000,
          "exogena": 120000000,
          "diferencia": 70000000,
          "variacion_pct": 140,
          "explicacion_ia": "El contribuyente declaró $50M en ICA..."
        }
      ],
      "explicacion_ia": "Contribuyente con alto riesgo de subdeclaración..."
    }
  ]
}
```

#### GET /proceso/{id}/errors — Consultar errores

**Query parameters:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `intento_id` | int | null | Filtrar por intento |
| `capa` | string | null | `MCP`, `ORACLE`, `LLM`, `POSTGRES`, `VALIDACION`, `PROCESO` |
| `nit` | string | null | Filtrar por NIT |

**Response (200):**
```json
{
  "proceso_id": "uuid-o-id-12345",
  "errores_proceso": [...],
  "errores_detalle": [...],
  "total_errores_proceso": 1,
  "total_errores_detalle": 5
}
```

#### GET /proceso/{id}/export — Exportar a XLSX

Descarga un archivo Excel con los resultados del proceso.

**Query parameters:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `formato` | string | `xlsx` | Formato de exportación |

**Response:** Archivo `.xlsx` con dos hojas:
- **Resumen:** ID, estado, totales
- **Resultados Campana:** NIT, razón social, CIIU, clasificación, scores, hallazgos, explicación IA

**Flujo de exportación:**

```mermaid
flowchart TD
    A["GET /proceso/id/export"] --> B["Validar proceso<br/>existe"]
    B --> C{"¿Existe?"}
    C -->|"No"| D["404<br/>ProcesoNoEncontrado"]
    C -->|"Sí"| E["SELECT proceso_detalle<br/>page_size=10000"]
    E --> F["Crear workbook<br/>openpyxl"]
    F --> G["Hoja 1: Resumen<br/>(ID, estado, totales)"]
    F --> H["Hoja 2: Resultados<br/>(NIT, scores, hallazgos)"]
    H --> I{"¿nivel_riesgo?"}
    I -->|"ALTO"| J["Fila roja<br/>(#F8D7DA)"]
    I -->|"MEDIO"| K["Fila amarilla<br/>(#FFF3CD)"]
    I -->|"BAJO"| L["Fila normal"]
    G --> M["StreamingResponse<br/>application/xlsx"]
    H --> M
    J --> M
    K --> M
    L --> M

    style A fill:#e3f2fd,stroke:#1565c0
    style D fill:#ffcdd2,stroke:#c62828
    style M fill:#c8e6c9,stroke:#2e7d32
```

**Flujo de consulta de resultados:**

```mermaid
flowchart TD
    A["GET /proceso/id/results"] --> B{"intento_id?"}
    B -->|"null"| C["Usar último intento"]
    B -->|"num"| D["Usar intento especificado"]
    C --> E{"include_partial?"}
    D --> E
    E -->|"false"| F{"Proceso terminado?"}
    F -->|"COMPLETADO"| G["SELECT paginado"]
    F -->|"EN_PROCESO / EN_COLA"| H["409 PROCESO_EN_PROCESO"]
    E -->|"true"| G
    G --> I{"Filtros?"}
    I -->|"clasificacion"| J["WHERE clasificacion = x"]
    I -->|"min_score"| K["WHERE mcp_score >= x"]
    I -->|"sin filtros"| L["ORDER BY + LIMIT/OFFSET"]
    J --> L
    K --> L
    L --> M["Retornar resultados + paginación"]
```

---

### 7.4. Análisis Individual

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/analizar/{contribuyente_nit}?periodo=2024` | Análisis on-demand (sin body) |

**Parámetros:**

| Parámetro | Tipo | Default | Requerido | Descripción |
|---|---|---|---|---|
| `contribuyente_nit` | string | — | Sí (path) | NIT del contribuyente a analizar |
| `periodo` | string | `2024` | No (query) | Año fiscal a analizar |

**Sin body** — el NIT va como path param y el período como query param.

**Response (200):**
```json
{
  "contribuyente_nit": "9012345678",
  "razon_social": "COMERCIO XYZ S.A.S.",
  "ciiu": "4711",
  "clasificacion": "INEXACTO",
  "mcp_score": 85.5,
  "mcp_razon": "",
  "srf_total": 78,
  "componentes_srf": [
    { "nombre": "consistencia", "valor": 80, "peso": 0.3 },
    { "nombre": "historial", "valor": 75, "peso": 0.4 },
    { "nombre": "declaracion", "valor": 82, "peso": 0.3 }
  ],
  "nivel_riesgo": "ALTO",
  "hallazgos": [...],
  "explicacion_ia": "Contribuyente con alto riesgo de subdeclaración...",
  "tokens_utilizados": 2500,
  "duracion_ms": 45000,
  "provider_utilizado": "anthropic",
  "cache_hit": false
}
```

**Comportamiento:**
- Timeout: 90 segundos máximo
- Cache: Si el mismo NIT + periodo fue analizado en < 1h, retorna cache
- No crea proceso en `procesos` (es análisis on-demand)

**Flujo del análisis individual:**

```mermaid
sequenceDiagram
    participant Client as Cliente
    participant API as FastAPI
    participant Cache as Cache
    participant Oracle as Oracle Database
    participant LLM as LLM Service

    Client->>API: POST /analizar/{nit}?periodo=2024
    API->>Cache: Buscar en caché (NIT + periodo)
    alt Cache hit
        Cache-->>API: Resultado缓存ado
        API-->>Client: 200 (respuesta缓存)
    else Cache miss
        API->>Oracle: obtener_datos_fiscales(nit)
        Oracle-->>API: datos fiscales
        API->>LLM: analizar(datos)
        LLM->>LLM: Tier 1 → Tier 2 → Tier 3
        LLM-->>API: hallazgos + explicación
        API->>Cache: Guardar resultado (TTL 1h)
        API-->>Client: 200 + resultados
    end
```

---

### 7.5. Análisis Comportamental

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/contribuyente/{nit}/comportamiento` | Análisis comportamental individual |
| `GET` | `/proceso/{id}/ranking-comportamental` | Ranking comportamental del proceso |
| `GET` | `/contribuyente/{nit}/grafo-riesgo` | Grafo de riesgo |
| `GET` | `/contribuyente/{nit}/expediente-fiscal` | Expediente fiscal consolidado |
| `GET` | `/visor/grafo/{nit}` | Visor HTML del grafo |

#### GET /contribuyente/{nit}/comportamiento

**Query parameters:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `periodo` | string | `2024` | Año fiscal |
| `ciiu` | string | null | Filtro por código CIIU |
| `regimen` | string | null | Filtro por régimen |
| `min_pares` | int | `10` | Mínimo de pares comparables (3-100) |

#### GET /contribuyente/{nit}/grafo-riesgo

**Query parameters:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `periodo` | string | `2024` | Año fiscal |
| `min_pares` | int | `10` | Mínimo de pares (3-100) |
| `incluir_comportamiento` | bool | `true` | Incluir datos comportamentales |

---

### 7.6. Fiscalización (Reglas R01-R10)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/fiscalizacion/reglas/evaluar` | Evaluar reglas sin persistir |
| `POST` | `/fiscalizacion/reglas/evaluar/{nit}` | Evaluar reglas por NIT |
| `POST` | `/fiscalizacion/reglas/ejecutar` | Ejecutar reglas y crear hallazgos |
| `POST` | `/fiscalizacion/reglas/ejecutar/{nit}` | Ejecutar reglas por NIT |
| `POST` | `/fiscalizacion/hallazgos` | Crear hallazgo manual |
| `POST` | `/fiscalizacion/hallazgos/desde-grafo/{nit}` | Crear hallazgo desde grafo |
| `GET` | `/fiscalizacion/hallazgos` | Listar hallazgos (paginado) |
| `GET` | `/fiscalizacion/hallazgos/{id}` | Obtener hallazgo |
| `POST` | `/fiscalizacion/hallazgos/{id}/revision` | Revisar hallazgo (humano) |
| `POST` | `/fiscalizacion/hallazgos/{id}/revision-agente` | Revisar hallazgo con IA |

#### POST /fiscalizacion/reglas/evaluar/{nit}

Evalúa las reglas fiscales para un NIT específico sin persistir resultados.

**Query parameters:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `periodo` | string | `2024` | Período fiscal |
| `reglas` | list | null | Filtrar reglas específicas (R01, R02, etc.) |

**Response (200):**
```json
{
  "total": 3,
  "resultados": [
    {
      "regla": "R01",
      "tipo_hallazgo": "OMISION",
      "fuerza_probatoria": "DIRECTA",
      "brecha_valor": 15000000,
      "score": 0.85
    }
  ]
}
```

#### GET /fiscalizacion/hallazgos — Listar hallazgos

**Query parameters:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `estado` | string | null | `DETECTADO`, `EN_REVISION`, `CONFIRMADO`, `DESCARTADO` |
| `regla` | string | null | Filtrar por regla (R01-R10) |
| `contribuyente_nit` | string | null | Filtrar por NIT |
| `accionable` | bool | null | Solo accionables |
| `page` | int | 1 | Página |
| `page_size` | int | 50 | Registros por página (max 200) |

**Flujo del motor de reglas fiscales:**

```mermaid
flowchart LR
    A["Perfil fiscal<br/>(datos Oracle)"] --> B["AplicarReglas<br/>R01-R10"]
    B --> C{"¿Regla<br/>aplica?"}
    C -->|"Sí"| D["Calcular brecha<br/>+ impuesto"]
    C -->|"No"| E["Descartar regla"]
    D --> F["Calcular score<br/>(confianza)"]
    F --> G{"¿score > 0.5?"}
    G -->|"Sí"| H["Crear hallazgo<br/>DETECTADO"]
    G -->|"No"| I["Registrar como<br/>info sin hallazgo"]
    H --> J["Persistir en<br/>hallazgos_fiscales"]
```

---

## 8. Ejemplos de Uso

### 8.1. curl — Crear proceso

```bash
curl -X POST http://localhost:8000/api/v1/proceso \
  -H "Content-Type: application/json" \
  -d '{
    "entidad_nit": "9003189639",
    "nombre": "Proceso Comercio Q1 2024",
    "vigencia_ini": "2024-01-01",
    "vigencia_fin": "2024-12-31",
    "tipo_regimen": "COMUN",
    "actividades_economicas": ["4711", "4712"],
    "periodo": "2024",
    "tipo": "COMPLETO",
    "max_nits": 0,
    "umbral_retenciones_pct": 5.0
  }'
```

### 8.2. curl — Consultar estado

```bash
curl http://localhost:8000/api/v1/proceso/{proceso_id}/status
```

### 8.3. curl — Consultar resultados

```bash
curl "http://localhost:8000/api/v1/proceso/{proceso_id}/results?page=1&page_size=20&clasificacion=INEXACTO"
```

### 8.4. curl — Análisis individual

```bash
curl -X POST "http://localhost:8000/api/v1/analizar/9012345678?periodo=2024"
```

### 8.5. curl — Evaluar reglas fiscales

```bash
curl -X POST "http://localhost:8000/api/v1/fiscalizacion/reglas/evaluar/9012345678?periodo=2024"
```

### 8.6. curl — Exportar resultados

```bash
curl -o resultados.xlsx "http://localhost:8000/api/v1/proceso/{proceso_id}/export?formato=xlsx"
```

### 8.7. Python — Conexión desde APEX/vía requests

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Crear proceso
response = requests.post(f"{BASE_URL}/proceso", json={
    "entidad_nit": "9003189639",
    "nombre": "Auditoría Q1 2024",
    "vigencia_ini": "2024-01-01",
    "vigencia_fin": "2024-12-31",
    "periodo": "2024",
    "tipo": "COMPLETO",
    "max_nits": 0,
    "umbral_retenciones_pct": 5.0
})
proceso_id = response.json()["proceso_id"]

# Polling de estado
import time
while True:
    status = requests.get(f"{BASE_URL}/proceso/{proceso_id}/status").json()
    if status["estado"] in ("COMPLETADO", "ERROR"):
        break
    time.sleep(5)

# Obtener resultados
results = requests.get(f"{BASE_URL}/proceso/{proceso_id}/results").json()
```

### 8.8. PL/SQL — Desde Oracle APEX

```sql
DECLARE
    l_response CLOB;
BEGIN
    l_response := apex_web_service.make_rest_request(
        p_url         => 'http://<container-ip>:8000/api/v1/analizar/9012345678?periodo=2024',
        p_http_method => 'POST'
    );
END;
```

---

## 9. Sistema de Fallback LLM

### 9.1. Cadena de Fallback

```mermaid
flowchart TD
    Request["Solicitud de análisis"] --> T1
    T1["Tier 1 — Anthropic Claude\n(o OpenAI GPT)"] -->|éxito| Response["Respuesta estructurada"]
    T1 -->|timeout/rate_limit/error| T2
    T2["Tier 2 — NVIDIA NIM\nQwen2.5-7B (gratis)"] -->|éxito| Response
    T2 -->|timeout/rate_limit/error| T3
    T3["Tier 3 — HuggingFace\nQwen2.5-7B (gratis)"] -->|éxito| Response
    T3 -->|fallo| Degrade["Resultado degradado + error registrado"]
```

### 9.2. Configuración de Providers

| Prioridad | Provider | Tipo | Modelo | API |
|---|---|---|---|---|
| Tier 1 | Anthropic | Pago | claude-sonnet-4-20250506 | Anthropic SDK |
| Tier 1 | OpenAI | Pago | gpt-4o | OpenAI SDK |
| Tier 2 | NVIDIA NIM | Gratis (5K credits) | qwen/qwen2.5-7b-instruct | OpenAI-compatible |
| Tier 3 | HuggingFace | Gratis (créditos mensuales) | Qwen/Qwen2.5-7B-Instruct | OpenAI-compatible |

### 9.3. Retry con Tenacity

```python
@tenacity.retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, max=10),
    retry=(retry_if_exception_type(TimeoutError) |
           retry_if_exception_type(RateLimitError) |
           retry_if_exception_type(APIError)),
)
async def call_provider(messages, schema):
    return await provider.chat_json(messages, schema)
```

### 9.4. Estrategia de Degradación

Cuando todos los providers fallan:
1. El NIT se marca con `LLM_ALL_PROVIDERS_FAILED` en `proceso_detalle_errores`
2. `explicacion_ia` queda como `null`
3. El proceso continúa con el siguiente NIT (no se aborta el batch)

---

## 10. Despliegue en OCI

### 10.1. Build de la Imagen Docker

```bash
# Construir
docker build -t iat/fiscalia-ia:latest .

# Taggear para OCI Registry
docker tag iat/fiscalia-ia:latest <region>.ocir.io/<namespace>/fiscalia-ia:latest

# Push
docker push <region>.ocir.io/<namespace>/fiscalia-ia:latest
```

### 10.2. Configuración OCI Container Instance

| Configuración | Valor |
|---|---|
| **VCN** | VCN existente del proyecto Taxation Smart |
| **Subred** | Privada (sin IP pública) |
| **NSG** | Regla de entrada solo desde IPs de APEX |
| **Puerto** | 8000 |
| **CPU** | 1 OCPU |
| **Memoria** | 8 GB |
| **Disco** | 10 GB |
| **Instancias** | 1 (V1) |

**Arquitectura de despliegue:**

```mermaid
flowchart TB
    subgraph OCI["☁️ Oracle Cloud Infrastructure"]
        subgraph VCN["VCN Privada"]
            subgraph SUBNET["Subnet Privada"]
                CI["Container Instance<br/>FiscalIA API<br/>:8000"]
            end
        end
        subgraph VAULT["OCI Vault"]
            V1["POSTGRES_PASSWORD"]
            V2["LLM_TIER1_API_KEY"]
            V3["LLM_TIER2_API_KEY"]
            V4["LLM_TIER3_API_KEY"]
        end
        subgraph LOGGING["OCI Logging"]
            LOG["Stdout logs"]
        end
    end

    subgraph EXT["Recursos Externos"]
        PG["PostgreSQL 16+<br/>10.0.1.100:5432"]
        ORA["Oracle 19c+<br/>(oracledb direct)"]
        LLM1["Anthropic API"]
        LLM2["NVIDIA NIM API"]
        LLM3["HuggingFace API"]
    end

    subgraph CLIENT["Clientes"]
        APEX["Oracle APEX<br/>Dynamic Actions"]
    end

    APEX -->|"HTTP (red privada)"| CI
    CI -->|"asyncpg"| PG
    CI -->|"oracledb"| ORA
    CI -->|"HTTPS"| LLM1
    CI -->|"HTTPS"| LLM2
    CI -->|"HTTPS"| LLM3
    VAULT -.->|"secrets"| CI
    CI -->|"stdout"| LOG

    style OCI fill:#e8eaf6,stroke:#283593,stroke-width:2px
    style EXT fill:#fff8e1,stroke:#f57f17,stroke-width:2px
    style CLIENT fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
```

### 10.3. Health Check

```
Ruta:       /api/v1/health
Puerto:     8000
Intervalo:  30s
Timeout:    10s
Umbral:     3 intentos fallidos
```

### 10.4. Variables en OCI Vault

Configurar todas las variables sensibles en **OCI Vault**, nunca en texto plano:
- `POSTGRES_PASSWORD`
- `LLM_TIER1_API_KEY`
- `LLM_TIER2_API_KEY`
- `LLM_TIER3_API_KEY`
- `ORACLE_PASSWORD`

---

## 11. Monitoreo y Alarmas

### 11.1. Logs

- OCI Logging recibe stdout del contenedor
- Cada análisis genera log estructurado: `nit`, `periodo`, `tiempo_ms`, `tokens`, `cache_hit`, `provider`

### 11.2. Métricas Clave

| Métrica | Target |
|---|---|
| Latencia POST /proceso | < 30s |
| Latencia POST /analizar/{nit} | < 90s |
| Cache hit ratio | > 30% |
| Errores 5xx | < 1% |
| Tokens consumidos/mes | Monitorear |

### 11.3. Alarmas Sugeridas

| Alarma | Umbral | Acción |
|---|---|---|
| Latencia > 90s | > 3 en 5 min | Notificar equipo |
| Errores 5xx | > 5 en 5 min | Notificar equipo |
| PostgreSQL caído | 1 ocurrencia | Notificar equipo |
| Costo LLM mensual | > $100 USD | Revisar uso |

---

## 12. Troubleshooting

### Errores Comunes

| Error | Causa | Solución |
|---|---|---|
| `ConfiguracionInvalidaError` | API key o password = "changeme" | Editar `.env` con valores reales |
| `PG_CONN_ERROR` | PostgreSQL no accesible | Verificar `POSTGRES_HOST`, firewall, pg_hba.conf |
| `MCP_TIMEOUT` | Oracle Database no responde | Verificar conexión oracledb, firewall, configuración Oracle |
| `ORACLE_NIT_NOT_FOUND` | NIT no encontrado en Oracle | Verificar el NIT en el padrón de contribuyentes |
| `LLM_ALL_PROVIDERS_FAILED` | Todos los LLM fallaron | Verificar API keys, créditos, rate limits |
| `PROCESO_EN_PROCESO` | Re-lanzar proceso en ejecución | Esperar a que termine o usar `include_partial=true` |
| `NIT_NO_ENCONTRADO` | NIT no existe en Oracle | Verificar el NIT en la fuente de datos |

### Comandos Útiles

```bash
# Ver logs en tiempo real
docker logs -f <container-id>

# Verificar conexión PostgreSQL
psql -h localhost -U fiscalia -d fiscalia -c "SELECT 1"

# Verificar pool de conexiones
curl http://localhost:8000/api/v1/health

# Tests de regresión
PYTHONPATH=microservice pytest tests/unit/ -v --tb=short

# Linting
ruff check microservice/ tests/
ruff format --check microservice/ tests/
```

---

## Rate Limiting

| Endpoint | Límite | Ventana |
|---|---|---|
| `POST /proceso` | 10 req | por minuto por IP |
| `GET /proceso/{id}/status` | 60 req | por minuto por IP |
| `GET /proceso/{id}/results` | 30 req | por minuto por IP |
| `GET /proceso/{id}/errors` | 30 req | por minuto por IP |
| `POST /analizar/{nit}` | 5 req | por minuto por IP |
| `GET /health` | Sin límite | — |

---

## Clasificación de Errores por Capa

| Capa | Códigos | Descripción |
|------|---------|-------------|
| `MCP` | `MCP_TIMEOUT`, `MCP_CONN_REFUSED`, `MCP_PAGE_ERROR` | Conexión Oracle Database (oracledb) |
| `ORACLE` | `ORACLE_QUERY_FAIL`, `ORACLE_TIMEOUT`, `ORACLE_NIT_NOT_FOUND` | Consultas Oracle 19c+ |
| `LLM` | `LLM_TIMEOUT`, `LLM_RATE_LIMIT`, `LLM_ALL_PROVIDERS_FAILED` | Proveedores LLM |
| `POSTGRES` | `PG_CONN_ERROR`, `PG_INSERT_FAIL` | Persistencia |
| `VALIDACION` | `CRITERIOS_INVALIDOS`, `NIT_NO_ENCONTRADO` | Validación entrada |
| `PROCESO` | `WORKER_TIMEOUT`, `ORCHESTRATION_FAIL` | Orquestación |

**Flujo de manejo de errores:**

```mermaid
flowchart TD
    A["Error en capa"] --> B{"¿Es FiscalIAError?"}
    B -->|"Sí"| C["error_handler.py<br/>Mapear a HTTP status"]
    B -->|"No"| D["Exception genérica<br/>→ 500 Internal Server Error"]
    C --> E["INSERT en<br/>proceso_errores<br/>o proceso_detalle_errores"]
    E --> F["Log estructurado<br/>+ request_id"]
    F --> G["Retornar JSON<br/>{error, mensaje, request_id}"]
    D --> E

    style A fill:#ffcdd2,stroke:#c62828
    style C fill:#c8e6c9,stroke:#2e7d32
    style D fill:#ffcdd2,stroke:#c62828
```

---

> **Autor:** FiscalIA Team  
> **Repositorio:** fiscalia-ia  
> **Licencia:** Uso interno — Municipio de Valledupar

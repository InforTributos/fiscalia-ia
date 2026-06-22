# Modelo de Datos — FiscalIA

> **Nota:** Este documento describe el modelo de datos **PostgreSQL** del microservicio Python, que reemplaza completamente el anterior modelo Oracle (`FISCAL_*` tables). La base de datos Oracle 19c+ del lado de Taxation Smart continúa existiendo como fuente de datos fiscales (consultada vía MCP Server), pero el estado de procesos, resultados MCP y resultados de análisis IA se persisten exclusivamente en PostgreSQL.

## 1. Descripción General

La base de datos PostgreSQL del microservicio consta de **6 tablas** que cubren el ciclo de vida completo de un proceso de fiscalización: desde la creación del proceso por parte de un cliente (auditor/fiscalizador), pasando por la obtención y clasificación de NITs vía MCP, hasta el análisis con LLM y el registro detallado de errores.

| Tabla | Propósito | Granularidad |
|-------|-----------|-------------|
| `clientes` | Consumidores de la API (auditores/fiscalizadores) | 1 fila por cliente |
| `procesos` | Cada criterio de fiscalización ejecutado | 1 fila por proceso |
| `proceso_intentos` | Cada ejecución o re-lanzamiento de un proceso | 1 fila por intento |
| `proceso_detalle` | NITs obtenidos del MCP y analizados por IA | 1 fila por NIT por intento |
| `proceso_errores` | Errores a nivel de proceso por intento | 1 fila por error |
| `proceso_detalle_errores` | Errores por NIT en el detalle | 1 fila por error |

---

## 2. Tablas

### 2.1. `clientes`

Registra los consumidores de la API — los auditores o fiscalizadores que lanzan procesos de fiscalización.

```sql
CREATE TABLE clientes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nit VARCHAR(20) UNIQUE NOT NULL,
    razon_social VARCHAR(500) NOT NULL,
    email VARCHAR(200),
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `UUID` | Identificador único del cliente, generado automáticamente |
| `nit` | `VARCHAR(20)` | NIT del cliente (auditor/fiscalizador), único |
| `razon_social` | `VARCHAR(500)` | Nombre o razón social del cliente |
| `email` | `VARCHAR(200)` | Correo electrónico de contacto |
| `activo` | `BOOLEAN` | Indica si el cliente está habilitado para usar la API |
| `created_at` | `TIMESTAMP` | Fecha y hora de registro |

**Índices:**

```sql
CREATE INDEX idx_clientes_nit ON clientes(nit);
```

---

### 2.2. `procesos`

Representa cada conjunto de criterios de fiscalización ejecutado. Un proceso puede tener múltiples intentos (re-lanzamientos).

```sql
CREATE TABLE procesos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id UUID REFERENCES clientes(id),
    nombre VARCHAR(200) NOT NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
    criteria JSONB NOT NULL,
    total_nits INTEGER DEFAULT 0,
    candidatos INTEGER DEFAULT 0,
    omisos INTEGER DEFAULT 0,
    exactos INTEGER DEFAULT 0,
    inexactos INTEGER DEFAULT 0,
    intentos_total INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `UUID` | Identificador único del proceso |
| `cliente_id` | `UUID` | FK → `clientes(id)`. Cliente que lanzó el proceso |
| `nombre` | `VARCHAR(200)` | Nombre descriptivo del proceso |
| `estado` | `VARCHAR(30)` | Estado actual del proceso (ver §4) |
| `criteria` | `JSONB` | Criterios de búsqueda (vigencia, régimen, CIIU, período) |
| `total_nits` | `INTEGER` | Total de NITs obtenidos del MCP |
| `candidatos` | `INTEGER` | NITs marcados como candidatos por el MCP |
| `omisos` | `INTEGER` | NITs clasificados como omisos |
| `exactos` | `INTEGER` | NITs clasificados como exactos (descartados) |
| `inexactos` | `INTEGER` | NITs clasificados como inexactos |
| `intentos_total` | `INTEGER` | Número total de intentos acumulados |
| `created_at` | `TIMESTAMP` | Fecha y hora de creación |

**Índices:**

```sql
CREATE INDEX idx_procesos_estado ON procesos(estado);
CREATE INDEX idx_procesos_cliente ON procesos(cliente_id);
```

---

### 2.3. `proceso_intentos`

Cada ejecución o re-lanzamiento de un proceso. Un proceso completado o en error puede ser re-lanzado, generando un nuevo intento con `numero_intento` incremental.

```sql
CREATE TABLE proceso_intentos (
    id SERIAL PRIMARY KEY,
    proceso_id UUID REFERENCES procesos(id),
    numero_intento INTEGER NOT NULL DEFAULT 1,
    estado VARCHAR(30) NOT NULL DEFAULT 'EN_PROCESO',
    procesados INTEGER DEFAULT 0,
    errores_count INTEGER DEFAULT 0,
    error_resumen TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `SERIAL` | Identificador único del intento |
| `proceso_id` | `UUID` | FK → `procesos(id)` |
| `numero_intento` | `INTEGER` | Número secuencial del intento (1, 2, 3...) |
| `estado` | `VARCHAR(30)` | Estado del intento |
| `procesados` | `INTEGER` | NITs procesados exitosamente hasta el momento |
| `errores_count` | `INTEGER` | Cantidad de errores registrados en este intento |
| `error_resumen` | `TEXT` | Resumen del error si el intento falló |
| `started_at` | `TIMESTAMP` | Fecha y hora de inicio del intento |
| `completed_at` | `TIMESTAMP` | Fecha y hora de finalización (nullable mientras está en curso) |

**Índices:**

```sql
CREATE INDEX idx_proceso_intentos_proceso ON proceso_intentos(proceso_id);
CREATE INDEX idx_proceso_intentos_estado ON proceso_intentos(estado);
```

---

### 2.4. `proceso_detalle`

Registro detallado de cada NIT obtenido del MCP, su clasificación (omiso/exacto/inexacto), los resultados del análisis del LLM (hallazgos, SRF, explicación) y métricas de consumo de tokens.

```sql
CREATE TABLE proceso_detalle (
    id SERIAL PRIMARY KEY,
    proceso_id UUID REFERENCES procesos(id),
    intento_id INTEGER REFERENCES proceso_intentos(id),
    nit VARCHAR(20) NOT NULL,
    razon_social VARCHAR(500),
    ciiu VARCHAR(10),
    mcp_score DECIMAL(10,2),
    es_candidato BOOLEAN DEFAULT TRUE,
    mcp_razon TEXT,
    clasificacion VARCHAR(20) NOT NULL,
    detalle_clasificacion TEXT,
    srf_total DECIMAL(5,2),
    nivel_riesgo VARCHAR(10),
    hallazgos JSONB,
    explicacion_ia TEXT,
    tokens_entrada INTEGER,
    tokens_salida INTEGER,
    costo_estimado DECIMAL(10,4),
    pagina INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `SERIAL` | Identificador único del detalle |
| `proceso_id` | `UUID` | FK → `procesos(id)` |
| `intento_id` | `INTEGER` | FK → `proceso_intentos(id)` |
| `nit` | `VARCHAR(20)` | NIT del contribuyente |
| `razon_social` | `VARCHAR(500)` | Razón social del contribuyente |
| `ciiu` | `VARCHAR(10)` | Código CIIU de la actividad económica |
| `mcp_score` | `DECIMAL(10,2)` | Score/peso asignado por el MCP al contribuyente |
| `es_candidato` | `BOOLEAN` | Indica si el MCP marcó al contribuyente como candidato a fiscalización |
| `mcp_razon` | `TEXT` | Razón proporcionada por el MCP para el score asignado |
| `clasificacion` | `VARCHAR(20)` | Clasificación del NIT: `OMISO`, `EXACTO`, `INEXACTO` |
| `detalle_clasificacion` | `TEXT` | Detalle o justificación de la clasificación |
| `srf_total` | `DECIMAL(5,2)` | Score de Riesgo Fiscal (0.00 — 100.00) |
| `nivel_riesgo` | `VARCHAR(10)` | Nivel de riesgo: `BAJO`, `MEDIO`, `ALTO` |
| `hallazgos` | `JSONB` | Hallazgos estructurados generados por el LLM |
| `explicacion_ia` | `TEXT` | Explicación en lenguaje natural generada por el LLM |
| `tokens_entrada` | `INTEGER` | Tokens consumidos en el prompt enviado al LLM |
| `tokens_salida` | `INTEGER` | Tokens generados en la respuesta del LLM |
| `costo_estimado` | `DECIMAL(10,4)` | Costo estimado en USD del análisis |
| `pagina` | `INTEGER` | Número de página MCP donde se obtuvo este NIT |
| `created_at` | `TIMESTAMP` | Fecha y hora de registro |

**Índices:**

```sql
CREATE INDEX idx_proceso_detalle_proceso ON proceso_detalle(proceso_id);
CREATE INDEX idx_proceso_detalle_intento ON proceso_detalle(intento_id);
CREATE INDEX idx_proceso_detalle_nit ON proceso_detalle(nit);
CREATE INDEX idx_proceso_detalle_clasificacion ON proceso_detalle(clasificacion);
```

---

### 2.5. `proceso_errores`

Errores a nivel de proceso por intento. Captura fallos en la comunicación con MCP, Oracle, LLM, PostgreSQL o en la orquestación general.

```sql
CREATE TABLE proceso_errores (
    id SERIAL PRIMARY KEY,
    proceso_id UUID REFERENCES procesos(id),
    intento_id INTEGER REFERENCES proceso_intentos(id),
    capa VARCHAR(30) NOT NULL,
    codigo VARCHAR(50) NOT NULL,
    mensaje TEXT NOT NULL,
    contexto JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `SERIAL` | Identificador único del error |
| `proceso_id` | `UUID` | FK → `procesos(id)` |
| `intento_id` | `INTEGER` | FK → `proceso_intentos(id)` |
| `capa` | `VARCHAR(30)` | Capa donde se originó el error (ver §6) |
| `codigo` | `VARCHAR(50)` | Código del error (ej: `MCP_TIMEOUT`, `LLM_ALL_PROVIDERS_FAILED`) |
| `mensaje` | `TEXT` | Mensaje descriptivo del error |
| `contexto` | `JSONB` | Contexto adicional estructurado (parámetros, tiempos, proveedores intentados) |
| `created_at` | `TIMESTAMP` | Fecha y hora del error |

**Índices:**

```sql
CREATE INDEX idx_proceso_errores_proceso ON proceso_errores(proceso_id);
CREATE INDEX idx_proceso_errores_intento ON proceso_errores(intento_id);
CREATE INDEX idx_proceso_errores_capa ON proceso_errores(capa);
```

---

### 2.6. `proceso_detalle_errores`

Errores específicos por NIT dentro del detalle de un proceso. Permite granularidad de 1 error por NIT o múltiples errores por NIT según el tipo de fallo.

```sql
CREATE TABLE proceso_detalle_errores (
    id SERIAL PRIMARY KEY,
    detalle_id INTEGER REFERENCES proceso_detalle(id),
    nit VARCHAR(20) NOT NULL,
    capa VARCHAR(30) NOT NULL,
    codigo VARCHAR(50) NOT NULL,
    mensaje TEXT NOT NULL,
    contexto JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | `SERIAL` | Identificador único del error |
| `detalle_id` | `INTEGER` | FK → `proceso_detalle(id)` |
| `nit` | `VARCHAR(20)` | NIT del contribuyente asociado al error |
| `capa` | `VARCHAR(30)` | Capa donde se originó el error (ver §6) |
| `codigo` | `VARCHAR(50)` | Código del error |
| `mensaje` | `TEXT` | Mensaje descriptivo del error |
| `contexto` | `JSONB` | Contexto adicional estructurado |
| `created_at` | `TIMESTAMP` | Fecha y hora del error |

**Índices:**

```sql
CREATE INDEX idx_detalle_errores_detalle ON proceso_detalle_errores(detalle_id);
```

---

## 3. Diagrama Entidad-Relación

```mermaid
erDiagram
    clientes ||--o{ procesos : "lanza"
    procesos ||--o{ proceso_intentos : "tiene"
    procesos ||--o{ proceso_detalle : "detalla"
    proceso_intentos ||--o{ proceso_errores : "registra"
    proceso_detalle ||--o{ proceso_detalle_errores : "puede tener"

    clientes {
        uuid id PK
        varchar nit UK
        varchar razon_social
        varchar email
        boolean activo
        timestamp created_at
    }

    procesos {
        uuid id PK
        uuid cliente_id FK
        varchar nombre
        varchar estado
        jsonb criteria
        int total_nits
        int candidatos
        int omisos
        int exactos
        int inexactos
        int intentos_total
        timestamp created_at
    }

    proceso_intentos {
        serial id PK
        uuid proceso_id FK
        int numero_intento
        varchar estado
        int procesados
        int errores_count
        text error_resumen
        timestamp started_at
        timestamp completed_at
    }

    proceso_detalle {
        serial id PK
        uuid proceso_id FK
        int intento_id FK
        varchar nit
        varchar razon_social
        varchar ciiu
        decimal mcp_score
        boolean es_candidato
        text mcp_razon
        varchar clasificacion
        text detalle_clasificacion
        decimal srf_total
        varchar nivel_riesgo
        jsonb hallazgos
        text explicacion_ia
        int tokens_entrada
        int tokens_salida
        decimal costo_estimado
        int pagina
        timestamp created_at
    }

    proceso_errores {
        serial id PK
        uuid proceso_id FK
        int intento_id FK
        varchar capa
        varchar codigo
        text mensaje
        jsonb contexto
        timestamp created_at
    }

    proceso_detalle_errores {
        serial id PK
        int detalle_id FK
        varchar nit
        varchar capa
        varchar codigo
        text mensaje
        jsonb contexto
        timestamp created_at
    }
```

---

## 4. Ciclo de Vida de los Procesos

### Estados

| Estado | Significado |
|--------|-------------|
| `PENDIENTE` | Proceso creado, esperando ejecución |
| `PREFILTRANDO` | El MCP está obteniendo NITs con paginación |
| `PREFILTRADO_COMPLETADO` | NITs obtenidos y clasificados, análisis IA encolado |
| `EN_COLA` | Esperando worker disponible (Procrastinate) |
| `EN_PROCESO` | Análisis IA en ejecución sobre los NITs |
| `COMPLETADO` | Todos los NITs han sido analizados exitosamente |
| `ERROR` | Error fatal en el proceso (ver `proceso_errores` para detalle) |
| `INTERRUMPIDO` | Contenedor reiniciado mientras el proceso estaba en ejecución. Recuperable mediante re-lanzamiento |

### Máquina de Estados

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
    INTERRUMPIDO --> EN_COLA: Restart manual (re-lanzamiento)
    ERROR --> [*]
    COMPLETADO --> [*]
```

### Re-lanzamiento

Cuando se envía el mismo `cliente_nit` + mismos `criteria` de un proceso previo:

| Situación | Comportamiento |
|-----------|---------------|
| Proceso `EN_PROCESO` con mismos criteria | Se rechaza con HTTP 409 `PROCESO_EN_PROCESO` |
| Proceso `COMPLETADO` o `ERROR` con mismos criteria | Se crea nuevo `proceso_intentos` con `numero_intento` incremental |
| Historial de intentos anteriores | Se preserva para consulta y auditoría |

---

## 5. Política de Retención de Datos

| Tabla | Retención | Acción |
|-------|-----------|--------|
| `procesos` | 2 años | DELETE después de 2 años |
| `proceso_intentos` | 2 años | DELETE en cascada desde `procesos` |
| `proceso_detalle` | 2 años | DELETE en cascada desde `procesos` |
| `proceso_errores` | 1 año | DELETE después de 1 año |
| `proceso_detalle_errores` | 1 año | DELETE después de 1 año |
| `clientes` | Indefinido | Nunca se eliminan (son cuentas de auditores) |
| Logs de aplicación | 6 meses | Rotación / archivado |

**Implementación:** Job mensual en PostgreSQL (cron o pg_timetable) que ejecuta las limpiezas según las ventanas de retención definidas.

---

## 6. Clasificación de Errores por Capa

El modelo utiliza una arquitectura hexagonal/DDD donde cada error se clasifica según la capa donde se originó, permitiendo filtrado granular en consultas y monitoreo.

| Capa | Códigos de ejemplo | Descripción |
|------|--------------------|-------------|
| `MCP` | `MCP_TIMEOUT`, `MCP_CONN_REFUSED`, `MCP_PAGE_ERROR` | Errores de conexión o comunicación con el MCP Server (FastMCP stdio) |
| `ORACLE` | `ORACLE_QUERY_FAIL`, `ORACLE_TIMEOUT`, `ORACLE_NIT_NOT_FOUND` | Errores en consultas a Oracle Database 19c+ (datos fiscales) |
| `LLM` | `LLM_TIMEOUT`, `LLM_RATE_LIMIT`, `LLM_INVALID_JSON`, `LLM_ALL_PROVIDERS_FAILED` | Errores en API de proveedores LLM (cualquier tier) |
| `POSTGRES` | `PG_CONN_ERROR`, `PG_INSERT_FAIL` | Errores de persistencia en PostgreSQL |
| `VALIDACION` | `CRITERIOS_INVALIDOS`, `NIT_NO_ENCONTRADO` | Errores de validación de entrada en los endpoints |
| `PROCESO` | `WORKER_TIMEOUT`, `ORCHESTRATION_FAIL` | Errores de orquestación general de procesos |

### Granularidad de errores por detalle

| Tipo de error | Granularidad | Ejemplo |
|---------------|-------------|---------|
| Timeout LLM para un NIT (todos los providers fallaron) | 1 error por NIT | `LLM_ALL_PROVIDERS_FAILED` |
| Datos faltantes del MCP | 1 error por NIT | `MCP_DATA_INCOMPLETE` |
| NIT no encontrado en Oracle | 1 error por NIT | `ORACLE_NIT_NOT_FOUND` |
| Múltiples validaciones fallidas | Múltiples por NIT | `VALIDACION_CIIU` + `VALIDACION_PERIODO` |

---

## 7. DDL Completo

El script DDL completo se encuentra en:

```
db/migrations/001_create_tables.sql
```

Incluye la creación de todas las tablas, relaciones, índices y la política de retención (job mensual).

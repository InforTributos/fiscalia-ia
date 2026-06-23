# Contrato MCP (Model Context Protocol)

> **Reemplaza el anterior Contrato PL/SQL** (`docs/03-contrato-plsql.md`).
> El microservicio consume datos fiscales vía Oracle MCP Server remoto con transporte Streamable HTTP.

---

## 1. Overview

El microservicio FiscalIA se comunica con Oracle Database exclusivamente a través del **Oracle MCP Server**, un servicio gestionado que expone tools PL/SQL genéricas vía el protocolo estándar MCP con transporte **Streamable HTTP + SSE**. A diferencia del contrato PL/SQL anterior —donde el microservicio llamaba directamente funciones de Oracle mediante `python-oracledb.callfunc()`—, ahora el microservicio envía peticiones HTTP autenticadas con Bearer Token al endpoint MCP de Oracle.

| Componente | Anterior | Actual |
|---|---|---|
| Transporte | `stdio` (subprocess local) | Streamable HTTP (remoto) |
| Autenticación | Ninguna | Bearer Token (OAuth 2.0 password grant) |
| Tools | Custom (`buscar_contribuyentes`, `obtener_datos_fiscales`) | Genéricas (`EXECUTE_SQL`, `LIST_OBJECTS`, `LIST_SCHEMAS`) |
| Librería cliente | `fastmcp.Client` | `mcp` SDK v1.28+ con `streamable_http_client` |

---

## 2. Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                   OCI Container Instance             │
│                                                      │
│  ┌──────────────────────┐                           │
│  │   Microservicio      │  HTTP POST (JSON-RPC 2.0) │
│  │   (FastAPI + Python) │ ───────────────────────►  │
│  │                      │   Authorization: Bearer   │
│  │   MCPClient          │ ◄───────────────────────  │
│  │   Pagination Loop    │   JSON-RPC Response       │
│  └──────────────────────┘                           │
│                                                      │
└──────────────────┬──────────────────────────────────┘
                   │
           HTTPS (red privada OCI)
                   │
┌──────────────────▼──────────────────────────────────┐
│              Oracle MCP Server                       │
│          (Oracle Database 23ai / 19c)                │
│                                                      │
│   Tools expuestas:                                   │
│   • EXECUTE_SQL  — ejecuta queries SQL               │
│   • LIST_OBJECTS — explora esquemas                  │
│   • LIST_SCHEMAS — lista esquemas disponibles        │
│                                                      │
└─────────────────────────────────────────────────────┘
```

- **Transporte:** Streamable HTTP (POST + SSE) — el microservicio envía peticiones HTTP al endpoint MCP de Oracle y recibe respuestas JSON-RPC 2.0.
- **Autenticación:** Bearer Token obtenido vía OAuth 2.0 Resource Owner Password Grant (`grant_type=password`).
- **Librería:** `mcp` SDK v1.28+ — `streamable_http_client` para el transporte, `ClientSession` para tool calls.
- **Ciclo de vida:** El microservicio obtiene un token fresco por cada llamada a tool. No hay conexión persistente.

---

## 3. Autenticación

### 3.1. Obtener Token

```
POST {MCP_TOKEN_URL}
Content-Type: application/x-www-form-urlencoded

grant_type=password&username={user}&password={password}
```

**Respuesta:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### 3.2. Usar Token en llamadas MCP

```
POST {MCP_SERVER_URL}
Authorization: Bearer {access_token}
Content-Type: application/json
```

> [!note] Token TTL
> El token es válido por 1 hora. El microservicio obtiene un token fresco en cada llamada a tool. Para producción, se recomienda cachear el token y refrescarlo solo cuando expire, pero la arquitectura actual prioriza simplicidad.

---

## 4. Tools del Oracle MCP Server

El Oracle MCP Server expone tools PL/SQL genéricas. El microservicio FiscalIA utiliza principalmente `EXECUTE_SQL`.

### 4.1. `EXECUTE_SQL`

**Parámetros de entrada:**

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `query` | `string` | Sí | SQL query con bind variables (`:nombre`) |
| `bind_params` | `object` | No | Mapa nombre → valor para bind variables |
| `offset` | `integer` | No | Offset para paginación (default: 0) |
| `limit` | `integer` | No | Límite de filas (default: 100, max: 500) |

**Output:** Lista de objetos con los nombres de columna como keys.

### 4.2. `LIST_SCHEMAS`

Lista los esquemas disponibles en la base de datos.

**Parámetros:**

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `offset` | `integer` | No | Offset para paginación |
| `limit` | `integer` | No | Límite de resultados |

### 4.3. `LIST_OBJECTS`

Lista los objetos (tablas, vistas) de un esquema.

**Parámetros:**

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `schema_name` | `string` | Sí | Nombre del esquema |
| `offset` | `integer` | No | Offset para paginación |
| `limit` | `integer` | No | Límite de resultados |

---

## 5. Queries Utilizadas

### 5.1. Paginación de contribuyentes

```sql
SELECT c.nit, c.razon_social, c.ciiu, c.regimen
FROM contribuyentes c
WHERE c.tipo_regimen = :tipo_regimen
  AND c.ciiu IN (:act1, :act2, ...)
  AND c.vigencia >= TO_DATE(:vigencia_ini, 'YYYY-MM-DD')
  AND c.vigencia <= TO_DATE(:vigencia_fin, 'YYYY-MM-DD')
ORDER BY c.nit
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
```

**Bind params:** `tipo_regimen`, `vigencia_ini`, `vigencia_fin`, `a0`, `a1`, ..., `offset`, `limit`

### 5.2. Obtener contribuyente

```sql
SELECT c.nit, c.razon_social, c.ciiu, c.regimen, r.rues_estado
FROM contribuyentes c
LEFT JOIN rues r ON c.nit = r.nit
WHERE c.nit = :nit
```

**Bind params:** `nit`

### 5.3. Obtener declaraciones ICA

```sql
SELECT periodo, base_gravable, tarifa, impuesto
FROM declaraciones_ica
WHERE nit = :nit AND periodo = :periodo
ORDER BY periodo
```

**Bind params:** `nit`, `periodo`

### 5.4. Obtener exógena DIAN

```sql
SELECT periodo, ingresos
FROM exogena_dian
WHERE nit = :nit AND periodo = :periodo
ORDER BY periodo
```

**Bind params:** `nit`, `periodo`

---

## 6. Estructura de datos esperada

### 6.1. Output combinado (tras múltiples queries)

```json
{
  "nit": "9012345678",
  "razon_social": "COMERCIO XYZ S.A.S.",
  "ciiu": "4711",
  "regimen": "COMUN",
  "declaraciones_ica": [
    {
      "periodo": "2024-B1",
      "base_gravable": 50000000,
      "tarifa": 0.01,
      "impuesto": 500000
    }
  ],
  "exogena_dian": [
    {
      "periodo": "2024",
      "ingresos": 120000000
    }
  ],
  "rues_estado": "ACTIVO"
}
```

### 6.2. Errores del MCP Server

| Condición | Código HTTP | Respuesta |
|---|---|---|
| Token inválido/expirado | 401 | `{"code": -32001, "message": "Unauthorized"}` |
| Query inválida | 400 | `{"code": -32602, "message": "Invalid params", "data": {"error": "ORA-00942: table or view does not exist"}}` |
| Timeout | 504 | `{"code": -32000, "message": "Request timeout"}` |

El microservicio maneja `401` obteniendo un nuevo token y reintentando automáticamente.

---

## 7. Protocolo de comunicación

### 7.1. Inicialización

```
POST {MCP_SERVER_URL}
Authorization: Bearer {token}
Content-Type: application/json

→ Request:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-03-26",
    "capabilities": {},
    "clientInfo": {"name": "fiscalia-ia", "version": "2.0.0"}
  }
}

← Response:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-03-26",
    "capabilities": {
      "tools": {}
    },
    "serverInfo": {"name": "oracle-mcp-server", "version": "1.0"}
  }
}
```

### 7.2. Descubrimiento de tools

```
→ Request:
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}

← Response:
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {"name": "EXECUTE_SQL", "description": "Execute SQL query", "inputSchema": {...}},
      {"name": "LIST_SCHEMAS", "description": "List available schemas", "inputSchema": {...}},
      {"name": "LIST_OBJECTS", "description": "List objects in a schema", "inputSchema": {...}}
    ]
  }
}
```

### 7.3. Ejecución de tool

```
→ Request:
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "EXECUTE_SQL",
    "arguments": {
      "query": "SELECT ... WHERE nit = :nit",
      "bind_params": {"nit": "9012345678"},
      "offset": 0,
      "limit": 10
    }
  }
}

← Response:
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "[{\"nit\": \"9012345678\", \"razon_social\": \"COMERCIO XYZ S.A.S.\", ...}]"
      }
    ]
  }
}
```

> [!note] Manejo de respuestas
> El contenido de `result.content[0].text` es un JSON string que el microservicio parsea automáticamente antes de retornarlo al caller.

---

## 8. Endpoints

### 8.1. Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `MCP_SERVER_URL` | Endpoint MCP del ADB | `https://dataaccess.adb.us-ashburn-1.oraclecloudapps.com/adb/mcp/v1/databases/ocid1...` |
| `MCP_TOKEN_URL` | Endpoint de autenticación OAuth | `https://dataaccess.adb.us-ashburn-1.oraclecloudapps.com/adb/auth/v1/databases/ocid1.../token` |
| `MCP_DB_USER` | Usuario de base de datos | `FISCALIA_APP` |
| `MCP_DB_PASSWORD` | Contraseña del usuario | — |
| `MCP_TIMEOUT` | Timeout por request (seg) | `30` |

### 8.2. Configuración en infraestructura

- El endpoint MCP se construye con el OCID de la Autonomous Database: `https://dataaccess.adb.{region}.oraclecloudapps.com/adb/mcp/v1/databases/{database-ocid}`
- El endpoint de token sigue el mismo patrón: `https://dataaccess.adb.{region}.oraclecloudapps.com/adb/auth/v1/databases/{database-ocid}/token`
- Ambos endpoints deben ser accesibles desde la red privada OCI del Container Instance

---

## 9. Escenarios de error

| Escenario | Código | Capa | Comportamiento del microservicio |
|---|---|---|---|
| Timeout al conectar con MCP Server | `MCP_TIMEOUT` | MCP | Reintento inmediato (hasta 3 intentos con backoff exponencial). Si persiste, proceso → `ERROR`. |
| Token inválido/expirado (401) | `MCP_AUTH_FAIL` | MCP | Obtiene nuevo token automáticamente y reintenta. Si falla de nuevo, proceso → `ERROR`. |
| Error en query SQL | `ORACLE_QUERY_FAIL` | ORACLE | Se registra el error y se reintenta la página (3 intentos). Si persiste, se omite y continúa. |
| NIT sin datos | `NIT_NO_ENCONTRADO` | VALIDACION | Se registra error por NIT y se continúa con el siguiente. |

---

## 10. Responsabilidades de cada fuente de datos

| Capa | Responsabilidad | Datos que entrega |
|---|---|---|
| **Oracle MCP Server** | Ejecutar queries SQL y retornar resultados estructurados | Filas de contribuyentes, declaraciones ICA, exógena DIAN, RUES |
| **Microservicio** (Python) | Orquestar queries, armar estructura anidada, clasificar NITs, enviar al LLM, persistir en PostgreSQL | NITs clasificados, hallazgos IA, SRF con explicación |
| **LLM Service** | Análisis semántico: explicación de brecha fiscal, hallazgos, recomendaciones | JSON estructurado con hallazgos, explicación y score |

---

## 11. Consideraciones finales

1. **El MCP Server es stateless** — no mantiene estado entre llamadas. Toda la paginación y contexto lo gestiona el microservicio.
2. **Sin conexión directa a Oracle** — el microservicio nunca usa `oracledb` ni `cx_Oracle`. Todos los datos fiscales se obtienen vía MCP.
3. **Tokens frescos** — por simplicidad, se obtiene un token nuevo en cada `call_tool`. Para producción, se recomienda cachear el token con refresh automático (TTL 1h).
4. **Versionado:** El contrato MCP se versiona mediante el campo `protocolVersion` en el mensaje `initialize`. El microservicio requiere `protocolVersion >= "2025-03-26"`.
5. **Trazabilidad:** Cada llamada a tool se loguea con `proceso_id`, `intento_id`, `duración_ms` y `NIT` (cuando aplica) para auditoría.

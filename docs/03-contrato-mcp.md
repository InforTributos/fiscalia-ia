# Contrato MCP (Model Context Protocol)

> **Reemplaza el anterior Contrato PL/SQL** (`docs/03-contrato-plsql.md`).  
> Las tools del MCP Server sustituyen las funciones de los packages `FISCAL_CROSS`, `FISCAL_INC` y `FISCAL_SCORE`.

---

## 1. Overview

El MCP Server expone dos tools que el microservicio Python consume vía el protocolo estándar MCP (Model Context Protocol) con transporte `stdio`. A diferencia del contrato PL/SQL anterior —donde el microservicio llamaba directamente funciones de Oracle mediante `python-oracledb.callfunc()`—, ahora el microservicio se comunica con un proceso MCP que encapsula el acceso a Oracle Database y retorna datos estructurados en JSON.

| Package PL/SQL (anterior) | Tool MCP (nuevo) | Propósito |
|---|---|---|
| `FISCAL_CROSS.obtener_cruces` | `buscar_contribuyentes` | Obtener NITs candidatos con score/razón |
| `FISCAL_CROSS.obtener_srf_base` | `obtener_datos_fiscales` + cálculo en MCP | Componentes SRF |
| `FISCAL_INC.obtener_inconsistencias` | `obtener_datos_fiscales` | Anomalías e inconsistencias |
| `FISCAL_SCORE.obtener_srf` | `obtener_datos_fiscales` + MCP score | Score de riesgo fiscal |
| `FISCAL_ANALISIS_IA.guardar` | *(eliminado — persistencia en PostgreSQL)* | Almacenamiento de resultados IA |

---

## 2. Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                   OCI Container Instance             │
│                                                      │
│  ┌──────────────────────┐     stdio subprocess      │
│  │   Microservicio      │ ◄───────────────────────  │
│  │   (FastAPI + Python) │                           │
│  │                      │   fastmcp.Client          │
│  │   AGT-05 MCP Client  │ ──► call_tool()           │
│  │   Pagination Loop    │ ──► discover_tools()      │
│  └──────────────────────┘                           │
│                                                      │
└──────────────────┬──────────────────────────────────┘
                   │
          stdio pipe (subprocess)
                   │
┌──────────────────▼──────────────────────────────────┐
│                   MCP Server                         │
│           (FastMCP — Oracle Database 19c+)           │
│                                                      │
│   Tools expuestas:                                   │
│   • buscar_contribuyentes                            │
│   • obtener_datos_fiscales                           │
│                                                      │
│   Conexión: oracledb → Oracle Database               │
└─────────────────────────────────────────────────────┘
```

- **Transporte:** `stdio` — el microservicio lanza el MCP Server como subproceso y se comunica por stdin/stdout con mensajes JSON-RPC.
- **Librería:** FastMCP v3.4.x (Python) — `fastmcp.Client` del lado del microservicio.
- **Ciclo de vida:** El microservicio inicia el subproceso MCP al arrancar y lo mantiene vivo; si el proceso MCP muere, el microservicio lo reinicia automáticamente (hasta 3 reintentos).

---

## 3. Tool: `buscar_contribuyentes`

### 3.1. Parámetros de entrada

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `vigencia_ini` | `string` (DATE) | Sí | Fecha inicial del período fiscal (YYYY-MM-DD) |
| `vigencia_fin` | `string` (DATE) | Sí | Fecha final del período fiscal (YYYY-MM-DD) |
| `tipo_regimen` | `string` | Sí | Tipo de régimen: `COMUN` o `SIMPLIFICADO` |
| `actividades_economicas` | `array[string]` | Sí | Lista de códigos CIIU (ej: `["4711","4712"]`) |
| `periodo` | `string` | Sí | Año fiscal (ej: `"2024"`) |
| `page` | `integer` | No | Número de página (default: `1`) |
| `page_size` | `integer` | No | Registros por página (default: `100`, max: `500`) |

### 3.2. Output por NIT

```json
{
  "nit": "9003189639",
  "score_peso": 75.5,
  "es_candidato": true,
  "razon": "Diferencia de ingresos del 45% entre exógena y declarado ICA para CIIU 4711"
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `nit` | `string` | NIT del contribuyente (sin guiones ni DV) |
| `score_peso` | `number` | Ponderación 0–100 calculada por el MCP |
| `es_candidato` | `boolean` | `true` si el contribuyente supera el umbral de fiscalización |
| `razon` | `string` | Razón textual que soporta la decisión (generada por el MCP con base en los cruces) |

### 3.3. Paginación

La tool implementa paginación obligatoria. El microservicio itera páginas secuencialmente hasta recibir una página vacía:

```
Request:    buscar_contribuyentes({..., page: 1, page_size: 100})
Response:   [100 NITs]

Request:    buscar_contribuyentes({..., page: 2, page_size: 100})
Response:   [100 NITs]

...

Request:    buscar_contribuyentes({..., page: N, page_size: 100})
Response:   []   ← página vacía → fin de la iteración
```

**Políticas:**
- El MCP Server debe retornar `[]` (arreglo vacío) cuando no hay más resultados.
- Cada página debe completarse en menos de 5 segundos (RNF-10).
- Si una página falla (timeout/error), el microservicio reintenta hasta 3 veces con backoff antes de marcar el proceso como `ERROR`.

### 3.4. Lógica interna del MCP (`es_candidato`)

El MCP Server aplica las siguientes reglas para determinar `es_candidato` y `score_peso`:

| Criterio | Peso en score | Descripción |
|---|---|---|
| Cruce exógena vs declarado ICA | 35% | Diferencia > umbral configurable (default 15%) |
| Antigüedad sin declarar | 20% | Meses desde la última declaración ICA |
| Discrepancia tarifa CIIU | 25% | Tarifa aplicada vs tarifa legal según CIIU |
| Estado RUES vs padrón ICA | 20% | Contribuyente activo en RUES pero omiso en ICA |

`es_candidato = true` si `score_peso >= 50` (umbral configurable en el MCP Server).

---

## 4. Tool: `obtener_datos_fiscales`

### 4.1. Parámetros de entrada

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `nit` | `string` | Sí | NIT del contribuyente (ej: `"9012345678"`) |
| `periodo` | `string` | Sí | Año fiscal (ej: `"2024"`) |

### 4.2. Output completo

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
    },
    {
      "periodo": "2024-B2",
      "base_gravable": 60000000,
      "tarifa": 0.01,
      "impuesto": 600000
    }
  ],
  "exogena_dian": [
    {
      "periodo": "2024",
      "ingresos": 120000000
    }
  ],
  "rues_estado": "ACTIVO",
  "rues_fecha_constitucion": "2015-03-15",
  "historial_anomalias": [
    {
      "periodo": "2024-B1",
      "base_anterior": 120000000,
      "base_actual": 50000000,
      "variacion_pct": -58.33,
      "alerta": true
    }
  ],
  "grupo_homogeneo": {
    "ciiu": "4711",
    "media_ingresos": 85000000,
    "mediana_ingresos": 72000000,
    "desviacion_ingresos": 35000000,
    "percentil_contribuyente": 65
  }
}
```

### 4.3. Campos del output

| Campo | Tipo | Descripción |
|---|---|---|
| `nit` | `string` | NIT del contribuyente |
| `razon_social` | `string` | Razón social |
| `ciiu` | `string` | Código CIIU principal |
| `regimen` | `string` | `COMUN` o `SIMPLIFICADO` |
| `declaraciones_ica` | `array` | Lista de declaraciones ICA del período (bimestres/meses) |
| `declaraciones_ica[].periodo` | `string` | Período de la declaración (ej: `"2024-B1"`) |
| `declaraciones_ica[].base_gravable` | `number` | Base gravable declarada en COP |
| `declaraciones_ica[].tarifa` | `number` | Tarifa aplicada (decimal, ej: `0.01` = 1%) |
| `declaraciones_ica[].impuesto` | `number` | Impuesto calculado en COP |
| `exogena_dian` | `array` | Ingresos reportados en exógena DIAN |
| `exogena_dian[].periodo` | `string` | Período (anual) |
| `exogena_dian[].ingresos` | `number` | Ingresos reportados en COP |
| `rues_estado` | `string` | Estado en RUES: `ACTIVO`, `SUSPENDIDO`, `CANCELADO` |
| `rues_fecha_constitucion` | `string` | Fecha de constitución (YYYY-MM-DD) |
| `historial_anomalias` | `array` | Alertas de variación > 30% vs período anterior |
| `historial_anomalias[].variacion_pct` | `number` | Variación porcentual |
| `historial_anomalias[].alerta` | `boolean` | `true` si `|variacion_pct| > 30` |
| `grupo_homogeneo` | `object` | Estadísticos del grupo de pares (mismo CIIU + ubicación + rango ingresos) |
| `grupo_homogeneo.percentil_contribuyente` | `number` | Percentil del contribuyente dentro de su grupo (0–100) |

### 4.4. Errores esperados

| Condición | Respuesta MCP |
|---|---|
| NIT no encontrado en Oracle | `{"error": "NIT_NOT_FOUND", "mensaje": "El NIT 9012345678 no existe en el padrón"}` |
| Período sin datos fiscales | `{"error": "NO_DATA_FOR_PERIOD", "mensaje": "No hay datos fiscales para el período 2024"}` |
| Error interno de base de datos | `{"error": "ORACLE_QUERY_FAIL", "mensaje": "Error al consultar datos del contribuyente"}` |

---

## 5. Responsabilidades de cada fuente de datos

| Capa | Responsabilidad | Datos que entrega |
|---|---|---|
| **MCP Server** (Oracle) | Obtener datos crudos desde Oracle Database: padrón ICA, declaraciones, exógena DIAN, RUES, catálogos | NITs candidatos con score, datos fiscales completos por NIT |
| **Microservicio** (Python) | Orquestar el pipeline: llamar MCP, clasificar NITs (omisos/exactos/inexactos), enviar al LLM, persistir en PostgreSQL | NITs clasificados, hallazgos IA, SRF con explicación |
| **LLM Service** | Análisis semántico: explicación de brecha fiscal, hallazgos de inexactitud, recomendaciones | JSON estructurado con hallazgos, explicación y score |

**Regla fundamental:** El MCP Server NO realiza análisis semántico ni genera explicaciones en lenguaje natural. Su función es entregar datos fiscales estructurados y aplicar reglas de negocio determinísticas (cálculo de score, detección de anomalías por umbral). El análisis profundo y la redacción de hallazgos es responsabilidad exclusiva del LLM Service vía el microservicio.

---

## 6. Escenarios de error

| Escenario | Código | Capa | Comportamiento del microservicio |
|---|---|---|---|
| Timeout al conectar con MCP Server | `MCP_TIMEOUT` | MCP | Reintento inmediato (hasta 3 intentos con backoff exponencial). Si persiste, proceso → `ERROR`. |
| Conexión rechazada (MCP no disponible) | `MCP_CONN_REFUSED` | MCP | El microservicio reinicia el subproceso MCP automáticamente (hasta 3 veces). Si falla, proceso → `ERROR`. |
| Error en página específica del MCP | `MCP_PAGE_ERROR` | MCP | Reintentar la página fallida (3 intentos). Si persiste, se omite la página y se registra en `proceso_errores`. El proceso continúa. |
| Datos incompletos del MCP para un NIT | `MCP_DATA_INCOMPLETE` | MCP | El NIT se marca como error en `proceso_detalle_errores`. Se continúa con el siguiente NIT. |
| Timeout de consulta Oracle | `ORACLE_TIMEOUT` | ORACLE | El MCP Server retorna error; el microservicio lo trata como `MCP_PAGE_ERROR` y reintenta. |
| NIT no encontrado en Oracle | `ORACLE_NIT_NOT_FOUND` | ORACLE | El MCP retorna el error correspondiente; el microservicio registra el error por NIT y continúa. |

**Almacenamiento de errores:** Todos los errores se persisten en `proceso_errores` (a nivel de proceso) y `proceso_detalle_errores` (a nivel de NIT) en PostgreSQL, con la siguiente estructura:

| Campo | Descripción |
|---|---|
| `capa` | `MCP`, `ORACLE`, `LLM`, `POSTGRES`, `VALIDACION`, `PROCESO` |
| `codigo` | Código del error (ej: `MCP_TIMEOUT`) |
| `mensaje` | Descripción textual del error |
| `contexto` | JSON con detalles adicionales (página, timeout_ms, NIT, etc.) |

---

## 7. Protocolo de descubrimiento

El MCP Server implementa el protocolo de descubrimiento estándar de MCP. El microservicio descubre las tools disponibles al iniciar la conexión `stdio`:

```
Cliente MCP                              Servidor MCP
    │                                         │
    │──── initialize(request_id, protocol) ──►│
    │◄─── initialized(server_capabilities) ──│
    │                                         │
    │──── tools/list(request_id) ────────────►│
    │◄─── tools/list(result: tools[]) ───────│
    │         [                               │
    │           {                             │
    │             name: "buscar_contribuyentes",│
    │             description: "...",          │
    │             inputSchema: {...}           │
    │           },                             │
    │           {                             │
    │             name: "obtener_datos_fiscales",│
    │             description: "...",          │
    │             inputSchema: {...}           │
    │           }                              │
    │         ]                                │
    │                                         │
    │──── tools/call(name, args) ────────────►│
    │◄─── tools/call(result: content) ───────│
```

El descubrimiento ocurre:
1. Al arrancar el microservicio (health check inicial).
2. Cada vez que el MCP Server se reinicia (el microservicio rediscovery automáticamente).
3. Bajo demanda vía el endpoint `GET /health` del microservicio, que verifica que las tools esperadas estén disponibles.

**Tools esperadas:** El microservicio valida que el MCP Server exponga exactamente dos tools:
- `buscar_contribuyentes`
- `obtener_datos_fiscales`

Si alguna falta, el microservicio registra una alerta y no permite ejecutar procesos hasta que el MCP Server esté correctamente configurado.

---

## 8. Consideraciones finales

1. **El MCP Server es stateless** — no mantiene estado entre llamadas. Toda la paginación y contexto lo gestiona el microservicio.
2. **Compatibilidad hacia atrás:** El MCP Server reemplaza completamente los packages PL/SQL `FISCAL_CROSS`, `FISCAL_INC` y `FISCAL_SCORE`. No hay convivencia entre ambos contratos.
3. **Versionado:** El contrato MCP se versiona mediante el campo `protocolVersion` en el mensaje `initialize`. El microservicio requiere `protocolVersion >= "2025-03-26"`.
4. **Trazabilidad:** Cada llamada a tool se loguea con `proceso_id`, `intento_id`, `duración_ms` y `NIT` (cuando aplica) para auditoría.

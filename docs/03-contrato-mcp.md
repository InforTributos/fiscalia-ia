# Contrato de Conexión a Oracle (oracledb directo)

> **Reemplaza el anterior Contrato MCP** (`docs/03-contrato-mcp.md` anterior).
> El microservicio se conecta a Oracle Database directamente mediante `python-oracledb`
> con un pool asíncrono de conexiones. No utiliza Oracle MCP Server en producción.

---

## 1. Overview

El microservicio FiscalIA se conecta a Oracle Database (Taxation Smart / GENESYS) a
través de un pool asíncrono de `oracledb`. No hay servidor MCP intermedio ni protocolo
de mensajería — el microservicio ejecuta SQL directamente sobre la base de datos fiscal.

| Componente | Anterior (MCP) | Actual |
|---|---|---|
| Transporte | Streamable HTTP + SSE | oracledb pool async (TCP directo) |
| Autenticación | Bearer Token (OAuth 2.0) | Usuario/contraseña de BD + ACL de red |
| Librería | `mcp` SDK v1.28+ | `oracledb` (python-oracledb) |
| Tools | `EXECUTE_SQL`, `LIST_OBJECTS` | SQL directo (`SELECT`, joins, CTEs) |
| Estado | Token por llamada | Pool persistente (min=4, max=20) |

---

## 2. Arquitectura

```
┌──────────────────────────────────────────────────────┐
│                OCI Container Instance                  │
│                                                        │
│  ┌──────────────────────────────────────────┐         │
│  │         Microservicio (FastAPI)           │         │
│  │                                            │         │
│  │  OracleClient (oracledb pool async)        │         │
│  │    ├── execute_sql(query, params)          │         │
│  │    └── execute_sql_raw(query, params)      │         │
│  │                                            │         │
│  │  RepositorioLookupOracle(OracleClient)     │         │
│  │    ├── get_impuesto_id("ICA")             │         │
│  │    ├── get_programa_id("O" | "OD" | "I")  │         │
│  │    ├── get_atributos_ica(periodo)          │         │
│  │    └── get_configuracion_declaracion()     │         │
│  │                                            │         │
│  │  pagination.py (generadores async)         │         │
│  │    ├── obtener_omisos_conocidos()          │         │
│  │    ├── obtener_omisos_desconocidos()       │         │
│  │    ├── obtener_inexactos_ciiu()            │         │
│  │    ├── obtener_inexactos_retenciones()     │         │
│  │    ├── obtener_datos_fiscales(nit)         │         │
│  │    └── paginar_contribuyentes()            │         │
│  └──────────────────────────────────────────┘         │
│                    │                                   │
│             Red privada OCI (TCP:1521)                 │
│                    │                                   │
└────────────────────┼──────────────────────────────────┘
                     │
┌────────────────────┼──────────────────────────────────┐
│                    ▼                                   │
│           Oracle Database 19c+ (OCI)                    │
│           Esquemas: GENESYS, FI_G, SI_I, GI_G          │
│                                                        │
│   Tablas principales:                                   │
│   • SI_C_SUJETOS — contribuyentes                       │
│   • SI_I_PERSONAS — datos de personas                   │
│   • SI_I_SUJETOS_IMPUESTO — relación sujeto-impuesto   │
│   • GI_G_DECLARACIONES — declaraciones ICA              │
│   • GI_G_EXOGENA_RETENCIONES — exógena DIAN            │
│   • GI_D_FORMULARIOS — tipos de formulario              │
│   • FI_G_CANDIDATOS — candidatos de fiscalización       │
│   • DF_C_IMPUESTOS — catálogo de impuestos              │
│   • DF_S_SUJETOS_ESTADO — estados del contribuyente     │
│   • FI_D_PROGRAMAS — programas de fiscalización         │
│   • TEMP_RQ_DIAN — data temporal de DIAN                │
└────────────────────────────────────────────────────────┘
```

---

## 3. Configuración

### 3.1. Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `ORACLE_HOST` | Host de Oracle | `10.0.1.100` |
| `ORACLE_PORT` | Puerto (default 1521) | `1521` |
| `ORACLE_SERVICE` | Service name | `GENESYS` |
| `ORACLE_USER` | Usuario BD | `FISCALIA_APP` |
| `ORACLE_PASSWORD` | Contraseña | — |
| `ORACLE_POOL_MIN` | Conexiones mínimas pool | `4` |
| `ORACLE_POOL_MAX` | Conexiones máximas pool | `20` |
| `ORACLE_POOL_TIMEOUT` | Timeout adquisición pool (seg) | `5` |

### 3.2. Conexión

El pool se inicializa al arrancar el microservicio (vía `OracleClient.initialize()`)
y se mantiene vivo durante toda la vida del proceso. El pool es global (singleton)
y compartido por todas las instancias de `OracleClient`.

```python
pool = oracledb.create_pool_async(
    user=settings.oracle_user,
    password=settings.oracle_password,
    dsn=oracledb.makedsn(settings.oracle_host, settings.oracle_port, service_name=settings.oracle_service),
    min=settings.oracle_pool_min,
    max=settings.oracle_pool_max,
    timeout=settings.oracle_pool_timeout,
)
```

---

## 4. Queries utilizadas

### 4.1. Obtener contribuyente por NIT

```sql
SELECT s.idntfccion AS nit, p.nmbre_rzon_scial AS razon_social,
       p.id_actvdad_ecnmca AS ciiu, se.cdgo_sjto_estdo AS regimen,
       si.id_sjto_impsto
FROM GENESYS.SI_C_SUJETOS s
JOIN GENESYS.SI_I_SUJETOS_IMPUESTO si ON s.id_sjto = si.id_sjto
JOIN GENESYS.SI_I_PERSONAS p ON si.id_sjto_impsto = p.id_sjto_impsto
LEFT JOIN GENESYS.DF_S_SUJETOS_ESTADO se ON si.id_sjto_estdo = se.id_sjto_estdo
JOIN GENESYS.DF_C_IMPUESTOS i ON si.id_impsto = i.id_impsto
WHERE s.idntfccion = :nit AND i.cdgo_impsto = 'ICA'
```

### 4.2. Declaraciones ICA

```sql
SELECT d.vgncia AS periodo, d.bse_grvble AS base_gravable,
       d.vlor_ttal AS impuesto, d.vlor_pago
FROM GENESYS.GI_G_DECLARACIONES d
JOIN GENESYS.GI_D_DCLRCNES_VGNCIAS_FRMLR dvf
    ON d.id_dclrcion_vgncia_frmlrio = dvf.id_dclrcion_vgncia_frmlrio
JOIN GENESYS.GI_D_FORMULARIOS f ON dvf.id_frmlrio = f.id_frmlrio
WHERE d.id_sjto_impsto = :id_sjto_impsto
  AND d.vgncia = :periodo
  AND d.cdgo_dclrcion_estdo = 'PRS'
  AND d.fcha_anlcion IS NULL
  AND f.cdgo_frmlrio LIKE 'FUN%'
```

### 4.3. Exógena DIAN

```sql
SELECT vgncia_rtncion AS periodo, SUM(vlor_rtncion) AS ingresos
FROM GENESYS.GI_G_EXOGENA_RETENCIONES
WHERE idntfccion = :nit AND vgncia_rtncion = :periodo
GROUP BY vgncia_rtncion
```

### 4.4. Descubrimiento de candidatos (pre-filtro batch)

El proceso `pre_filtrar()` en `tasks/analisis_task.py` ejecuta 4 queries de descubrimiento:

| Query | Clasificación | Fuente |
|---|---|---|
| `OMISOS_CONOCIDOS_SQL` | OMISO | Contribuyentes registrados sin declaraciones ICA |
| `OMISOS_DESCONOCIDOS_DIAN_SQL` | OMISO | Detectados por DIAN, no registrados en el municipio |
| `INEXACTOS_CIIU_SQL` | INEXACTO | CIIU declarado vs DIAN con discrepancia |
| `INEXACTOS_RETENCIONES_SQL` | INEXACTO | Retenciones ICA vs exógena con diferencia > umbral |

---

## 5. Clasificación post-consulta

Una vez obtenidos los datos fiscales, se clasifica al contribuyente:

| Condición | Clasificación |
|---|---|
| Sin declaraciones ICA en el período → | **OMISO** |
| Declaraciones ICA vs exógena DIAN coinciden → | **EXACTO** |
| Anomalías en CIIU, tarifa o retenciones → | **INEXACTO** |

---

## 6. Paginación

Todas las queries de descubrimiento usan paginación con `OFFSET / FETCH NEXT ROWS ONLY`
(Oracle 12c+), con tamaño de página configurable (`page_size=100` por defecto).

Cada función devuelve un generador async (`async generator`). El caller itera hasta
que el generador se agota (última página con menos filas que `page_size`).

---

## 7. LookupRepository

El `RepositorioLookupOracle` centraliza consultas paramétricas con caché en memoria:

| Método | Cache | Propósito |
|---|---|---|
| `get_impuesto_id(cdgo_impsto)` | Sí | Resuelve IDs de impuestos (ICA, ICO, etc.) |
| `get_programa_id(cdgo_prgrma)` | Sí | Resuelve IDs de programas (O, OD, I) |
| `get_atributos_ica(periodo)` | Sí | IDs de atributos CIIU, tarifas, retenciones |
| `get_configuracion_declaracion()` | Sí | Configuración de presentación de declaraciones |

---

## 8. Escenarios de error

| Escenario | Código | Capa | Comportamiento |
|---|---|---|---|
| Timeout de conexión | `ORACLE_TIMEOUT` | ORACLE | Se reintenta (3 intentos). Si persiste, proceso → `ERROR`. |
| Pool sin conexiones disponibles | `PG_CONN_ERROR` | POSTGRES | Error del pool asyncpg (no Oracle). |
| Query inválida (tabla no existe) | `ORACLE_QUERY_FAIL` | ORACLE | Se registra error por NIT y se continúa. |
| Ningún generador funciona | `MCP_ALL_FAIL` | MCP | Proceso → `ERROR`. |
| NIT sin datos en Oracle | `NIT_NO_ENCONTRADO` | VALIDACION | Se omite y se continúa. |

---

## 9. Consideraciones finales

1. **Pool persistente**: El pool de oracledb se crea una vez al arrancar y se reusa.
   No hay overhead de conexión por request.
2. **Sin servidor MCP**: No se utiliza Oracle MCP Server en producción. La conexión
   es directa para minimizar latencia y dependencias.
3. **Red privada**: Oracle solo es accesible desde la red privada OCI del Container Instance.
4. **Solo lectura**: El microservicio solo ejecuta `SELECT` — nunca escribe en Oracle.
5. **Cache local**: El `RepositorioLookupOracle` cachea resultados de catálogos
   (impuestos, programas, atributos) para reducir queries repetitivas.
6. **Trazabilidad**: Cada query se loguea con `proceso_id`, `intento_id` y duración.

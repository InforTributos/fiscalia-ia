# Contrato PL/SQL — Interfaz esperada por el Microservicio

El microservicio Python se comunica con Oracle Database mediante **llamadas a funciones PL/SQL** usando `python-oracledb.callfunc()`. Este documento define el contrato exacto que deben implementar los packages del lado Oracle.

## 1. FISCAL_CROSS (AGT-01 CrossCheck)

### Función: `obtener_cruces`

```sql
FUNCTION FISCAL_CROSS.obtener_cruces(
    p_nit      VARCHAR2,      -- NIT del contribuyente (ej: '9003189639')
    p_periodo  VARCHAR2       -- Período (ej: '2025-01')
) RETURN SYS_REFCURSOR;
```

**Columnas del cursor retornado:**

| Columna | Tipo | Descripción |
|---|---|---|
| `ciiu` | VARCHAR2(10) | Código CIIU de la actividad |
| `ingreso_declarado` | NUMBER(18,2) | Ingreso declarado en ICA |
| `ingreso_exogena` | NUMBER(18,2) | Ingreso reportado en exógena |
| `diferencia` | NUMBER(18,2) | Diferencia en COP (exógena - declarado) |
| `variacion_pct` | NUMBER(10,2) | Variación porcentual |
| `umbral_superado` | NUMBER(1) | 1 si diferencia > umbral configurado |

### Función: `obtener_srf_base`

```sql
FUNCTION FISCAL_CROSS.obtener_srf_base(
    p_nit      VARCHAR2,
    p_periodo  VARCHAR2
) RETURN SYS_REFCURSOR;
```

**Columnas del cursor:**

| Columna | Tipo | Descripción |
|---|---|---|
| `srf_total` | NUMBER(5,2) | Score total 0-100 |
| `comp_exogena` | NUMBER(5,2) | Componente exógena |
| `comp_tarifa` | NUMBER(5,2) | Componente tarifa CIIU |
| `comp_omision` | NUMBER(5,2) | Componente omisión |
| `comp_rues` | NUMBER(5,2) | Componente RUES |

---

## 2. FISCAL_INC (AGT-03 InconsistencyAnalyzer)

### Función: `obtener_inconsistencias`

```sql
FUNCTION FISCAL_INC.obtener_inconsistencias(
    p_nit      VARCHAR2,
    p_periodo  VARCHAR2
) RETURN SYS_REFCURSOR;
```

**Columnas del cursor retornado:**

| Columna | Tipo | Descripción |
|---|---|---|
| `tipo_incidencia` | VARCHAR2(50) | SUBREGISTRO, TARIFA, PERIODO, EXENCION, BASE_CERO, OTRA |
| `ciiu` | VARCHAR2(10) | CIIU donde se detectó |
| `descripcion` | VARCHAR2(500) | Descripción textual |
| `valor_declarado` | NUMBER(18,2) | Valor declarado en ICA |
| `valor_referencia` | NUMBER(18,2) | Valor de referencia |
| `diferencia` | NUMBER(18,2) | Diferencia en COP |
| `severidad` | VARCHAR2(10) | ALTA, MEDIA, BAJA |

---

## 3. FISCAL_SCORE

### Función: `obtener_srf`

```sql
FUNCTION FISCAL_SCORE.obtener_srf(
    p_nit      VARCHAR2,
    p_periodo  VARCHAR2
) RETURN SYS_REFCURSOR;
```

**Columnas del cursor:**

| Columna | Tipo | Descripción |
|---|---|---|
| `srf_total` | NUMBER(5,2) | Score total 0-100 |
| `comp_exogena` | NUMBER(5,2) | Componente exógena |
| `comp_tarifa` | NUMBER(5,2) | Componente tarifa CIIU |
| `comp_omision` | NUMBER(5,2) | Componente omisión |
| `comp_rues` | NUMBER(5,2) | Componente RUES |

---

## 4. FISCAL_ANALISIS_IA

### Procedimiento: `guardar`

```sql
PROCEDURE FISCAL_ANALISIS_IA.guardar(
    p_expediente_id   NUMBER,       -- ID del expediente (NULL si no aplica)
    p_tipo_analisis   VARCHAR2,     -- 'COMPLETO' | 'SRF'
    p_prompt          CLOB,         -- Prompt enviado al LLM
    p_respuesta_ia    CLOB,         -- Respuesta del LLM
    p_tokens_entrada  NUMBER,       -- Tokens del prompt
    p_tokens_salida   NUMBER,       -- Tokens de la respuesta
    p_costo_estimado  NUMBER,       -- Costo estimado USD
    p_cache_hit       NUMBER DEFAULT 0  -- 1 si fue de caché
);
```

---

## 5. Consideraciones

1. **Cada llamada es síncrona** — el microservicio espera la respuesta de Oracle
2. **Todas las funciones reciben VARCHAR2** — el microservicio pasa los strings formateados (NIT sin guiones, período en formato YYYY-MM)
3. **No se requiere manejo transaccional** desde el microservicio — cada operación es autónoma
4. **El DDL completo** de los packages stub está en `db/migrations/002_contratos_plsql.sql`

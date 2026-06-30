# Design: Alinear FiscalIA con metodologia real de candidatos ICA

## Components

### `pagination.py` — Reescritura de queries + funciones nuevas

**Funciones que cambian:**

| Funcion actual | Cambio |
|---|---|
| `obtener_datos_fiscales(client, nit, periodo)` | Mantiene firma. Cambian queries internas a tablas reales. |
| `paginar_contribuyentes(...)` | Mantiene firma. Cambia SQL a query de omisos conocidos + filtro exclusion. |

**Funciones nuevas:**

| Funcion | Proposito |
|---|---|
| `obtener_omisos_desconocidos(client, vigencia, page_size)` | Cruce DIAN + exogena vs SI_C_SUJETOS |
| `obtener_inexactos_ciiu(client, periodo, page_size)` | Cruce CIIU declarado vs DIAN |
| `obtener_inexactos_retenciones(client, periodo, page_size, umbral_pct)` | Cruce retenciones declaradas vs exogena |
| `_verificar_exclusion_omisos(client, nit, vigencia, periodo)` | Helper: verifica si NIT ya tiene expediente FI_* de omisos |
| `_verificar_exclusion_inexactos(client, nit, vigencia, periodo)` | Helper: verifica si NIT ya tiene expediente FI_* de inexactos |

### `classify.py` — Expansion

**Nueva funcion principal:**

```python
def clasificar_candidato(item: dict) -> tuple[str, str]:
```

Soporta 5 tipos:
- `OMISO_CONOCIDO` — no declaro, estaba registrado
- `OMISO_DESCONOCIDO` — no registrado, detectado por DIAN/exogena
- `INEXACTO_CIIU` — declaro con CIIU de menor tarifa
- `INEXACTO_RETENCIONES` — diferencia en retenciones
- `EXACTO` — sin anomalias

**Funcion legacy mantenida:**
```python
def clasificar_nit(mcp_item: dict) -> tuple[str, str]:
```
Sigue funcionando con logica antigua como fallback.

## Data Model

### Mapeo de tablas Oracle

| Nombre generico (actual) | Nombre real (nuevo) |
|---|---|
| `contribuyentes` | `SI_C_SUJETOS` + `SI_I_PERSONAS` + `SI_I_SUJETOS_IMPUESTO` |
| `declaraciones_ica` | `GI_G_DECLARACIONES` |
| `exogena_dian` | `GI_G_EXOGENA_RETENCIONES` (retenciones) + `TEMP_RQ_DIAN` (ingresos DIAN) |
| `rues` | *(no tiene equivalente directo — se usa `SI_I_PERSONAS` para CIIU y estado)* |

### Estructura de item por tipo de candidato

**Omiso Conocido:**
```json
{
  "tipo": "OMISO_CONOCIDO",
  "nit": "9003189639",
  "razon_social": "COMERCIO XYZ S.A.S.",
  "ciiu": "4711",
  "direccion": "Calle 10 #5-30",
  "regimen": "COMUN",
  "fecha_inicio_actividades": "2015-03-15",
  "periodos_omisos": ["2024-B1", "2024-B2", "2024-B3"],
  "total_periodos_omisos": 3,
  "id_sjto_impsto": 12345
}
```

**Omiso Desconocido:**
```json
{
  "tipo": "OMISO_DESCONOCIDO",
  "nit": "9012345678",
  "razon_social": "EMPRESA NO REGISTRADA S.A.",
  "ciiu": "4721",
  "fuente": "DIAN",
  "valor_ingresos_estimado": 150000000,
  "vigencia": "2024"
}
```

**Inexacto CIIU:**
```json
{
  "tipo": "INEXACTO_CIIU",
  "nit": "9003189639",
  "razon_social": "COMERCIO XYZ S.A.S.",
  "ciiu_declarado": "4711",
  "tarifa_declarada": 0.008,
  "ciiu_dian": "4721",
  "tarifa_dian": 0.010,
  "diferencia_tarifa": 0.002,
  "periodo": "2024"
}
```

**Inexacto Retenciones:**
```json
{
  "tipo": "INEXACTO_RETENCIONES",
  "nit": "9003189639",
  "razon_social": "COMERCIO XYZ S.A.S.",
  "retenciones_declaradas_practicadas": 500000,
  "retenciones_exogena_practicadas": 750000,
  "diferencia_pct": 33.3,
  "retenciones_declaradas_recibidas": 300000,
  "retenciones_exogena_recibidas": 310000,
  "diferencia_recibidas_pct": 3.2,
  "periodo": "2024"
}
```

## API Contracts

Las funciones en `pagination.py` mantienen la interfaz `async def funcion(client: MCPClient, ...) -> AsyncGenerator[dict, None] | dict | None`.

Todas usan `client.call_tool("EXECUTE_SQL", {"query": sql, "bind_params": {...}})`.

## Queries SQL principales

### Omisos Conocidos

```sql
SELECT p.nmbre_rzon_scial, s.idntfccion, p.id_actvdad_ecnmca,
       si.id_sjto_impsto, si.id_sjto_estdo, p.fcha_incio_actvddes,
       s.drccion
FROM SI_I_SUJETOS_IMPUESTO si
JOIN SI_I_PERSONAS p ON si.id_sjto = p.id_sjto
JOIN SI_C_SUJETOS s ON si.id_sjto = s.id_sjto
WHERE si.id_impsto = (SELECT id_impsto FROM SI_D_IMPUESTOS WHERE cdgo = 'ICA')
  AND si.estdo_blqdo = 'N'
  AND p.fcha_incio_actvddes <= TO_DATE(:fin_periodo, 'YYYY-MM-DD')
  AND (si.fcha_cnclcion IS NULL OR si.fcha_cnclcion > TO_DATE(:fin_periodo, 'YYYY-MM-DD'))
  AND NOT EXISTS (
    SELECT 1 FROM GI_G_DECLARACIONES d
    WHERE d.id_sjto_impsto = si.id_sjto_impsto
      AND d.vgncia = :vigencia
      AND d.cdgo_dclrcion_estdo IN ('VIGENTE', 'PRESENTADA')
      AND d.fcha_anlcion IS NULL
  )
  AND NOT EXISTS (
    SELECT 1 FROM FI_G_CANDIDATOS c
    JOIN FI_G_CANDIDATOS_VIGENCIA cv ON c.id_cnddto = cv.id_cnddto
    JOIN FI_G_FSCLZC_EXPDN_CNDD_VGNC ev ON cv.id_cnddto_vgncia = ev.id_cnddto_vgncia
    WHERE c.id_sjto_impsto = si.id_sjto_impsto
      AND c.id_prgrma = (SELECT id_prgrma FROM FI_D_PROGRAMAS WHERE cdgo_prgrma = 'O')
      AND cv.vgncia = :vigencia
  )
ORDER BY s.idntfccion
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
```

### Omisos Desconocidos (fuente DIAN)

```sql
SELECT d.nit, d.razon_social, d.ciiu, d.valor_dian, d.vgncia
FROM TEMP_RQ_DIAN d
WHERE d.vgncia = :vigencia
  AND NOT EXISTS (
    SELECT 1 FROM SI_C_SUJETOS s WHERE s.idntfccion = d.nit
  )
  AND NOT EXISTS (
    SELECT 1 FROM FI_G_CANDIDATOS c
    JOIN FI_G_CANDIDATOS_VIGENCIA cv ON c.id_cnddto = cv.id_cnddto
    WHERE c.id_sjto_impsto IN (
      SELECT si.id_sjto_impsto FROM SI_I_SUJETOS_IMPUESTO si
      JOIN SI_C_SUJETOS s ON si.id_sjto = s.id_sjto
      WHERE s.idntfccion = d.nit
    )
    AND c.id_prgrma = (SELECT id_prgrma FROM FI_D_PROGRAMAS WHERE cdgo_prgrma = 'O')
    AND cv.vgncia = :vigencia
  )
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
```

### Inexactos CIIU

```sql
SELECT s.idntfccion, p.nmbre_rzon_scial,
       det_ciiu.vlor AS ciiu_declarado,
       det_tarifa.vlor AS tarifa_declarada,
       dian.ciiu AS ciiu_dian,
       dian.trfa AS tarifa_dian
FROM GI_G_DECLARACIONES decl
JOIN SI_I_SUJETOS_IMPUESTO si ON decl.id_sjto_impsto = si.id_sjto_impsto
JOIN SI_I_PERSONAS p ON si.id_sjto = p.id_sjto
JOIN SI_C_SUJETOS s ON si.id_sjto = s.id_sjto
JOIN GI_G_DECLARACIONES_DETALLE det_ciiu
  ON decl.id_dclrcion = det_ciiu.id_dclrcion
  AND det_ciiu.id_frmlrio_rgion_atrbto IN (5086, 4725)
JOIN GI_G_DECLARACIONES_DETALLE det_tarifa
  ON decl.id_dclrcion = det_tarifa.id_dclrcion
  AND det_tarifa.id_frmlrio_rgion_atrbto IN (5004)
JOIN TEMP_RQ_DIAN dian ON s.idntfccion = dian.nit AND dian.vgncia = :vigencia
WHERE decl.vgncia = :vigencia
  AND decl.cdgo_dclrcion_estdo IN ('VIGENTE', 'PRESENTADA')
  AND decl.fcha_anlcion IS NULL
  AND det_ciiu.vlor != dian.ciiu
  AND TO_NUMBER(det_tarifa.vlor) < TO_NUMBER(dian.trfa)
  AND NOT EXISTS (
    SELECT 1 FROM FI_G_CANDIDATOS c
    JOIN FI_G_CANDIDATOS_VIGENCIA cv ON c.id_cnddto = cv.id_cnddto
    WHERE c.id_sjto_impsto = si.id_sjto_impsto
      AND c.id_prgrma = (SELECT id_prgrma FROM FI_D_PROGRAMAS WHERE cdgo_prgrma = 'I')
      AND cv.vgncia = :vigencia
  )
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
```

### Inexactos Retenciones

```sql
SELECT s.idntfccion, p.nmbre_rzon_scial,
       det_ret_recibidas.vlor AS retenciones_declaradas_recibidas,
       det_ret_practicadas.vlor AS retenciones_declaradas_practicadas,
       exo_recibidas.total AS retenciones_exogena_recibidas,
       exo_practicadas.total AS retenciones_exogena_practicadas
FROM GI_G_DECLARACIONES decl
JOIN SI_I_SUJETOS_IMPUESTO si ON decl.id_sjto_impsto = si.id_sjto_impsto
JOIN SI_I_PERSONAS p ON si.id_sjto = p.id_sjto
JOIN SI_C_SUJETOS s ON si.id_sjto = s.id_sjto
LEFT JOIN GI_G_DECLARACIONES_DETALLE det_ret_recibidas
  ON decl.id_dclrcion = det_ret_recibidas.id_dclrcion
  AND det_ret_recibidas.id_frmlrio_rgion_atrbto IN (717, 845, 1190, 5035)
LEFT JOIN GI_G_DECLARACIONES_DETALLE det_ret_practicadas
  ON decl.id_dclrcion = det_ret_practicadas.id_dclrcion
  AND det_ret_practicadas.id_frmlrio_rgion_atrbto IN (718, 846, 5036)
LEFT JOIN (
  SELECT idntfccion, SUM(vlor_rtncion) AS total
  FROM GI_G_EXOGENA_RETENCIONES
  WHERE vgncia_rtncion = :vigencia
    AND cdgo_exgna_tpo_rgstro = 'RECIBIDA'
  GROUP BY idntfccion
) exo_recibidas ON s.idntfccion = exo_recibidas.idntfccion
LEFT JOIN (
  SELECT idntfccion, SUM(vlor_rtncion) AS total
  FROM GI_G_EXOGENA_RETENCIONES
  WHERE vgncia_rtncion = :vigencia
    AND cdgo_exgna_tpo_rgstro = 'PRACTICADA'
  GROUP BY idntfccion
) exo_practicadas ON s.idntfccion = exo_practicadas.idntfccion
WHERE decl.vgncia = :vigencia
  AND decl.cdgo_dclrcion_estdo IN ('VIGENTE', 'PRESENTADA')
  AND decl.fcha_anlcion IS NULL
  AND (
    ABS(NVL(TO_NUMBER(det_ret_recibidas.vlor), 0) - NVL(exo_recibidas.total, 0))
      > :umbral * GREATEST(NVL(TO_NUMBER(det_ret_recibidas.vlor), 0), NVL(exo_recibidas.total, 0), 1)
    OR
    ABS(NVL(TO_NUMBER(det_ret_practicadas.vlor), 0) - NVL(exo_practicadas.total, 0))
      > :umbral * GREATEST(NVL(TO_NUMBER(det_ret_practicadas.vlor), 0), NVL(exo_practicadas.total, 0), 1)
  )
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
```

## Dependencies

- Sin nuevas librerias Python
- Oracle MCP Server con acceso a todas las tablas listadas
- Tabla `SI_D_IMPUESTOS` (catalogo de impuestos) — asumida existente
- Tabla `FI_D_PROGRAMAS` con codigos 'O' (Omisos) e 'I' (Inexactos) — asumida existente

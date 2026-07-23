# Anexo Técnico — Pesos, Umbrales y Fuentes de Datos

> **Versión:** 1.0  
> **Audiencia:** Equipo técnico, implementadores  
> **Propósito:** Detalle exacto de pesos, umbrales, fórmulas y tablas Oracle para trazabilidad completa

---

## 1. Fuentes de Datos Oracle

### 1.1. Esquema: GENESYS

| Tabla | Alias | Propósito | Columnas clave |
|---|---|---|---|
| `SI_C_SUJETOS` | `s` | Sujetos tributarios | `id_sjto`, `cdgo_clnte`, `idntfccion` (NIT) |
| `SI_I_SUJETOS_IMPUESTO` | `si` | Relación sujeto-impuesto | `id_sjto_impsto`, `id_sjto`, `id_impsto`, `estdo_blqdo` |
| `SI_I_PERSONAS` | `p` | Datos persona | `id_sjto_impsto`, `nmbre_rzon_scial`, `id_actvdad_ecnmca` (CIIU) |
| `DF_S_SUJETOS_ESTADO` | `se` | Estado/régimen | `id_sjto_estdo`, `cdgo_sjto_estdo` |
| `DF_C_IMPUESTOS` | `i` | Catálogo impuestos | `id_impsto`, `cdgo_impsto` |
| `GI_G_DECLARACIONES` | `d` | Declaraciones ICA | `id_dclrcion`, `id_sjto_impsto`, `vgncia`, `bse_grvble`, `vlor_ttal`, `cdgo_dclrcion_estdo` |
| `GI_D_DCLRCNES_VGNCIAS_FRMLR` | `dvf` | Vínculo declaración-formulario | `id_dclrcion_vgncia_frmlrio` |
| `GI_D_FORMULARIOS` | `f` | Formularios | `id_frmlrio`, `cdgo_frmlrio` |
| `GI_G_EXOGENA_RETENCIONES` | — | Exógena MUNICIPAL de retenciones ICA | `idntfccion`, `vgncia_rtncion`, `vlor_bse` (base, usado en R3), `vlor_rtncion` (retención), `trfa`, `cdgo_exgna_tpo_rgsto` ('RD' recibida/'RP' practicada) |
| `GI_G_DECLARACIONES_DETALLE` | — | Detalle de declaraciones | `id_dclrcion`, `id_frmlrio_rgion_atrbto`, `vlor` |
| `DF_S_CLIENTES` | `c` | Maestro clientes | `cdgo_clnte`, `drccion`, `tlfno`, `email` |
| `TEMP_RQ_DIAN` | `dian` | Datos temporales DIAN | `nit`, `ciiu`, `tarifa`, `vigencia`, `valor_dian` |
| `FI_G_CANDIDATOS` | — | Candidatos fiscalización | `id_sjto_impsto`, `id_prgrma`, `id_cnddto` |
| `FI_G_CANDIDATOS_VIGENCIA` | — | Vigencia candidatos | `id_cnddto`, `vgncia` |

### 1.2. Constantes del lookup

| Constante | Valor | Significado |
|---|---|---|
| `ID_IMPSTO_ICA` | 102 | ID del impuesto ICA en `DF_C_IMPUESTOS` |
| `CDGO_IMPSTO_ICA` | 'ICA' | Código del impuesto ICA |
| `ID_PRGRMA_OMISOS` | 2 | ID del programa "OMISOS" en `FI_D_PROGRAMAS` |
| `ID_PRGRMA_INEXACTOS` | 22 | ID del programa "INEXACTOS" en `FI_D_PROGRAMAS` |

### 1.3. Filtros de declaraciones vigentes

```sql
d.cdgo_dclrcion_estdo = 'PRS'   -- Presentada
AND d.fcha_anlcion IS NULL       -- No anulada
AND f.cdgo_frmlrio LIKE 'FUN%'   -- Formulario FUN (no otras declaraciones)
```

---

## 2. SRF — Pesos y Fórmulas

### 2.1. Componentes

```python
COMPONENTES_SRF = {
    "diferencia_exogena":  {"peso": 35, "nombre": "Diferencia exógena vs ICA"},
    "antiguedad_omision":  {"peso": 20, "nombre": "Antigüedad sin declarar"},
    "discrepancia_tarifa": {"peso": 25, "nombre": "Discrepancia tarifa CIIU"},
    "estado_rues":         {"peso": 20, "nombre": "Estado RUES vs padrón"},
}
```

### 2.2. Cálculo por componente

**Diferencia exógena (0-35):**
```python
diff_pct = (ingresos_exogena - total_declarado) / total_declarado
# Se activa si diff_pct > 0.15 (15%)
valor = min(diff_pct * 35, 35)
```

**Antigüedad omisión (0-20):**
```python
PERIODOS_ESPERADOS = 6
if not declaraciones:
    valor = 20
else:
    valor = max(0, (PERIODOS_ESPERADOS - len(declaraciones)) / PERIODOS_ESPERADOS * 20)
```

**Discrepancia tarifa (0-25):**
```python
# Por cada declaración con tarifa distinta a la oficial
valor = min(max(discrepancias) * 250, 25)
```

**Estado RUES (0-20):**
```python
if estado in ("INACTIVO", "SUSPENDIDO"):
    valor = 20
elif not estado:
    valor = 10
else:
    valor = 0
```

### 2.3. Nivel de riesgo

```python
if srf_total >= 70:   nivel = "ALTO"
elif srf_total >= 40: nivel = "MEDIO"
else:                 nivel = "BAJO"
```

---

## 3. Score Comportamental — Pesos y Umbrales

### 3.1. Indicadores

```python
INDICADORES = {
    "BASE_GRAVABLE_BAJO_P10":       {"pts": 30, "severidad": "ALTA"},
    "BASE_GRAVABLE_BAJO_P25":       {"pts": 18, "severidad": "MEDIA"},
    "SUBDECLARACION_RELATIVA_SECTOR": {"pts": 25, "severidad": "ALTA"},
    "DESVIACION_RELEVANTE_SECTOR":  {"pts": 15, "severidad": "MEDIA"},
    "EXOGENA_CON_DECLARACION_CERO": {"pts": 35, "severidad": "ALTA"},
    "EXOGENA_ALTA_DECLARACION_BAJA": {"pts": 25, "severidad": "ALTA"},
    "EXOGENA_SUPERA_DECLARACION":   {"pts": 15, "severidad": "MEDIA"},
    "TARIFA_EFECTIVA_ATIPICA":      {"pts": 10, "severidad": "MEDIA"},
    "OUTLIER_INFERIOR_GRUPO_COMPARABLE": {"pts": 10, "severidad": "MEDIA"},
}
```

### 3.2. Condiciones de activación

```python
# BASE_GRAVABLE_BAJO_P10
base <= p10_base_gravable

# BASE_GRAVABLE_BAJO_P25
p10_base_gravable < base <= p25_base_gravable

# SUBDECLARACION_RELATIVA_SECTOR
variacion_mediana <= -0.70  # base es <= 30% de la mediana

# DESVIACION_RELEVANTE_SECTOR
-0.70 < variacion_mediana <= -0.50  # base entre 30% y 50% de la mediana

# EXOGENA_CON_DECLARACION_CERO
base == 0 AND ingresos_exogena > 0

# EXOGENA_ALTA_DECLARACION_BAJA
ratio_exogena_declarado >= 3

# EXOGENA_SUPERA_DECLARACION
ratio_exogena_declarado >= 2 AND ratio_exogena_declarado < 3

# TARIFA_EFECTIVA_ATIPICA
tarifa_efectiva < mediana_tarifa_efectiva * 0.5  # menos del 50% de la mediana

# OUTLIER_INFERIOR_GRUPO_COMPARABLE
zscore_robusto <= -2.5
```

### 3.3. Variación y z-score

```python
variacion_mediana = (base - mediana_base) / mediana_base  # si mediana > 0
percentil = percentile_rank(bases_del_grupo, base) * 100
zscore = robust_zscore(bases_del_grupo, base)
# robust_zscore = 0.6745 * (target - mediana) / MAD
# MAD = median(abs(values - median(values)))
```

### 3.4. Confianza

```python
if total_pares >= 100:  confianza = 0.9
elif total_pares >= 30: confianza = 0.75
elif total_pares >= 10: confianza = 0.6
else:                   confianza = 0.4
```

### 3.5. Prioridad

```python
if score >= 80:  prioridad = "ALTA"
elif score >= 55: prioridad = "MEDIA"
else:            prioridad = "BAJA"
```

---

## 4. Reglas Fiscales — Detalle

### 4.1. Catálogo

```python
RULES_CATALOG = {
    "R1": {"nombre": "Retención sin declaración suficiente", "fuerza": "DIRECTA"},
    "R2": {"nombre": "Omiso con presencia registral", "fuerza": "DIRECTA"},
    "R3": {"nombre": "Brecha exógena DIAN", "fuerza": "DIRECTA"},
    "R4": {"nombre": "Brecha facturación electrónica", "fuerza": "DIRECTA"},
    "R5": {"nombre": "Contratista estatal no declarante", "fuerza": "DIRECTA"},
    "R6": {"nombre": "Declarante en cero persistente", "fuerza": "INDICIARIA"},
    "R7": {"nombre": "CIIU conveniente", "fuerza": "MEDIA"},
    "R8": {"nombre": "Atípico sectorial", "fuerza": "INDICIARIA"},
    "R9": {"nombre": "Territorialidad", "fuerza": "MEDIA"},
    "R10": {"nombre": "Caída abrupta de base", "fuerza": "INDICIARIA"},
}
```

### 4.2. Umbrales por regla

| Regla | Parámetro | Valor default |
|---|---|---|
| R1 | `tolerancia` | 5% |
| R1 | `tarifa_retencion` | 0.011 (11 por mil) |
| R3 | `threshold` | 15% |
| R4 | `tolerancia` | 5% |
| R6 | `declaraciones_cero_min` | 2 |
| R7 | — | Compara tarifa declarada vs tarifa oficial del CIIU |
| R8 | `percentil_min` | <= 10 |
| R10 | `umbral_caida` | 60% |

### 4.3. Tarifas CIIU por defecto

```python
TARIFAS_CIIU_DEFAULT = {
    "4711": 0.008,  # Comercio al por menor
    "4712": 0.008,
    "4721": 0.006,  # Alimentos
    "5611": 0.010,  # Comidas preparadas
    "6820": 0.005,  # Inmobiliarias
    "8511": 0.004,  # Educación
    "6201": 0.003,  # Desarrollo de software
    "6202": 0.003,
}
```

---

## 5. Score Unificado

### 5.1. Fórmula

```python
score_unificado = (
    score_comportamental * 0.30 +
    score_srf           * 0.20 +
    score_reglas        * 0.20 +
    score_red           * 0.15 +
    score_temporal      * 0.10 +
    confianza * 100     * 0.05
)
```

### 5.2. Sub-scores

**Score reglas:**
```python
PROBATORIA_SCORE = {"DIRECTA": 100, "MEDIA": 65, "INDICIARIA": 35}
score = probatoria * 0.6 + brecha_relativa * 0.4
```

**Score temporal:**
```python
score = min(score_severidad + len(hallazgos) * 10, 100)
score_severidad = promedio ponderado: ALTA=100, MEDIA=65, BAJA=35
```

### 5.3. Bonos

| Condición | +Pts |
|---|---|
| `empresas_conectadas >= 3` y `score_comportamental >= 70` | +5 |
| Hallazgo `EXOGENA_CON_DECLARACION_CERO` | +8 |
| Hallazgo con `fuerza_probatoria == "DIRECTA"` | +10 |
| Hallazgo temporal `DESAPARICION_DECLARATIVA` | +5 |

### 5.4. Prioridad

```python
if score >= 90:  prioridad = "CRITICA"
elif score >= 75: prioridad = "ALTA"
elif score >= 50: prioridad = "MEDIA"
else:            prioridad = "BAJA"
```

---

## 6. Patrones Temporales — Umbrales

```python
# CAIDA_ABRUPTA
UMBRAL_CAIDA = 0.60  # 60%

# TENDENCIA_DESCENDENTE
PERIODOS_CONSECUTIVOS = 3
UMBRAL_TENDENCIA = 0.50  # 50% caída acumulada

# DIVERGENCIA_EXOGENA
UMBRAL_CREC_EXOGENA = 0.10  # 10% crecimiento
FACTOR_DIVERGENCIA = 0.50   # base crece menos del 50% del crecimiento de exógena

# VOLATILIDAD
CV_UMBRAL = 0.50           # 50% coeficiente de variación
PERIODOS_MIN = 4

# DESAPARICION
# No requiere umbral configurable: detecta si el período actual no tiene declaración
```

### 6.1. Asignación de severidad temporal

```python
SEVERIDAD_TEMPORAL = {
    "CAIDA_ABRUPTA_TEMPORAL": "ALTA",
    "TENDENCIA_DESCENDENTE": "ALTA" if caida > 0.50 else "MEDIA",
    "DIVERGENCIA_EXOGENA_CRECIENTE": "ALTA" if (crec_exogena > 0.30 and crec_base < 0) else "MEDIA",
    "VOLATILIDAD_SOSPECHOSA": "MEDIA",
    "DESAPARICION_DECLARATIVA": "ALTA",
}
```

---

## 7. Hallazgos — Scoring

### 7.1. Fórmula de scoring

```python
score_hallazgo = (
    0.35 * fuerza_probatoria +
    0.30 * monto +
    0.15 * urgencia +
    0.10 * reincidencia +
    0.10 * corroboracion
)
```

### 7.2. Cálculo de sub-componentes

```python
# Fuerza probatoria
{"DIRECTA": 100, "MEDIA": 60, "INDICIARIA": 30}

# Monto
min(impuesto_estimado / 100_000_000 * 100, 100)

# Urgencia (días hasta prescripción)
if dias <= 180:   100
elif dias <= 365: 75
elif dias <= 730: 45
else:             20

# Reincidencia
min(contador_historial * 25, 100)

# Corroboración (fuentes cruzadas)
min(cantidad_fuentes * 25, 100)
```

### 7.3. Bandas de prioridad

```python
if score >= 80:  banda = "A"
elif score >= 60: banda = "B"
elif score >= 40: banda = "C"
else:            banda = "D"
```

> **Nota:** `DIRECTA`, `MEDIA` e `INDICIARIA` son valores de **fuerza probatoria** de las reglas fiscales (R01-R10). No confundir con `ALTA`/`MEDIA`/`BAJA` que es la **severidad** usada en hallazgos comportamentales. El score de hallazgo usa fuerza probatoria.

---

## 8. Ventana Legal

### 8.1. Plazos (Colombia)

```python
VENCIMIENTO_DECLARACION = "04-30"  # 30 de abril del año siguiente
FIRMEZA_ANOS = 3                    # 3 años desde vencimiento
AFORO_OMISOS_ANOS = 5               # 5 años desde vencimiento
```

### 8.2. Cálculo

```python
def vencimiento(periodo):
    return date(int(periodo) + 1, 4, 30)

def fecha_firmeza(periodo):
    return vencimiento(periodo) + timedelta(days=365 * FIRMEZA_ANOS)

def fecha_aforo(periodo):
    return vencimiento(periodo) + timedelta(days=365 * AFORO_OMISOS_ANOS)

def es_accionable(periodo, clasificacion):
    limite = fecha_aforo(periodo) if clasificacion == "OMISO" else fecha_firmeza(periodo)
    return date.today() <= limite
```

---

## 9. Grafo de Riesgo — Bonos por Conexión

### 9.1. Tipos de arista

```python
BONOS_CONEXION = {
    "COMPARTE_REPRESENTANTE": 8,
    "COMPARTE_DIRECCION": 6,
    "COMPARTE_TELEFONO": 4,
    "COMPARTE_CORREO": 4,
}
```

### 9.2. Bonos compuestos

```python
# Empresas multi-atributo (comparten >=2 atributos con el mismo NIT)
multi_atributo = min(empresas_multi * 5, 20)

# Red de alto riesgo
if score_comportamental >= 70 and empresas_conectadas >= 3:
    bono_red_alto_riesgo = 10

# Hallazgos severos
bono_hallazgos = min(hallazgos_severidad_alta * 3, 12)

# Bono máximo total: 35 pts
bono_total = min(sum(bonos), 35)
```

### 9.3. Score de red

```python
score_red = min(score_comportamental + bono_total, 100)
```

---

## 10. Revisión Automática de Hallazgos

> ⚠️ **No implementado actualmente.** Esta sección describe el diseño planeado para la revisión automática de hallazgos, pero el código actual no incluye este paso. Los hallazgos se crean directamente en estado `DETECTADO` y pasan a revisión humana sin filtro automático intermedio.

### 10.1. Verificación de completitud

```python
completitud = 100
if not evidencias:              completitud -= 35
por cada falta:                 completitud -= 15  (máx -45)
por cada riesgo:                completitud -= 10  (máx -30)
if not resumen:                 completitud -= 10
if not accionable:              completitud -= 25
```

### 10.2. Estados según completitud

```python
if completitud >= 80 and sin_faltantes:  estado = "COMPLETO"
elif completitud >= 55:                  estado = "REQUIERE_AJUSTES"
else:                                    estado = "INCOMPLETO"
```

### 10.3. Acción recomendada

```python
if completitud >= 80 and score >= 80:
    accion = "Pasar a revisión humana prioritaria"
elif completitud >= 80:
    accion = "Pasar a cola de revisión humana"
elif hay_faltantes:
    accion = "Completar evidencia antes de asignar al fiscalizador"
elif hay_riesgos:
    accion = "Revisar riesgos jurídicos antes de avanzar"
else:
    accion = "Mantener en monitoreo"
```

---

## 11. CIIU con Mayor Cantidad de Contribuyentes Activos ICA

| CIIU | Total contribuyentes |
|---|---|
| 3693 | 873 |
| 3518 | 513 |
| 3690 | 405 |
| 3190 | 248 |
| 2215 | 225 |
| 3519 | 202 |
| 2132 | 196 |
| 3182 | 182 |
| 3324 | 180 |
| 3254 | 163 |
| 3146 | 157 |
| 3250 | 148 |
| 3179 | 124 |
| 3523 | 112 |

---

*Documento generado el 16/07/2026 — Sistema FiscalIA v2.0.0*

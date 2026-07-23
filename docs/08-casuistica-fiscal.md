# Sistema de Fiscalización ICA — Casuística y Reglas de Análisis

> **Versión:** 2.0.0  
> **Audiencia:** Product Owner, equipo de negocio  
> **Propósito:** Describir la lógica de negocio del sistema de fiscalización asistido por IA para el Impuesto de Industria y Comercio (ICA)

---

## 1. Flujo General del Proceso

Cada proceso de fiscalización recorre las siguientes etapas:

```
INICIO → PRE-FILTRO → CLASIFICACIÓN → ANÁLISIS → HALLAZGOS → REVISIÓN
```

1. **Inicio**: Un funcionario crea un proceso especificando período, CIIU, y número máximo de contribuyentes a analizar
2. **Pre-filtro**: El sistema descubre contribuyentes desde Oracle aplicando 4 estrategias de búsqueda
3. **Clasificación**: Cada contribuyente se clasifica como OMISO, EXACTO o INEXACTO
4. **Análisis**: Se ejecutan en paralelo: cruce SRF, score comportamental, reglas fiscales, patrones temporales
5. **Hallazgos**: Se consolidan todos los hallazgos detectados con su severidad
6. **Revisión**: Los hallazgos pasan por revisión automática y pueden asignarse a fiscalizadores humanos

---

## 2. Fuentes de Datos

El sistema consulta dos fuentes de datos:

### Oracle GENESYS (Base transaccional del municipio)
- **SI_C_SUJETOS + SI_I_PERSONAS**: Datos del contribuyente (NIT, razón social, CIIU)
- **GI_G_DECLARACIONES**: Declaraciones de ICA presentadas al municipio. Columna clave: `BSE_GRVBLE` (base gravable declarada)
- **GI_G_EXOGENA_RETENCIONES**: Exógena **municipal** de retenciones de ICA. NO es exógena DIAN.
  - `VLOR_BSE` = base de la operación (ingreso real del contribuyente)
  - `VLOR_RTNCION` = valor de la retención
  - `cdgo_exgna_tpo_rgstro`: `'RD'` (retención recibida — le retuvieron al contribuyente), `'RP'` (retención practicada — él retuvo a otros)
- **GI_G_EXOGENA_INGR_FRA_MUNI**: Exógena municipal de ingresos por fracción territorial (para territorialidad R9). 183k registros
- **GI_G_EXOGENA_INGR_NO_GRAVDS**: Exógena municipal de ingresos no gravados con ICA. 1.6M registros
- **GI_G_INTERMEDIA_DIAN**: Intermediación DIAN — datos que la DIAN comparte con el municipio basados en facturación electrónica y RUT. Contiene `TTAL_INGRSOS_GRVBLE` (ingresos gravables ICA del contribuyente según DIAN). 7.600 registros (2021-2025)
- **TEMP_RQ_DIAN**: Datos temporales de DIAN para cruce CIIU/tarifa (R4, R7)
- **DF_S_CLIENTES**: Datos de contacto (dirección, teléfono, correo)
- **DF_S_SUJETOS_ESTADO**: Estado/régimen del contribuyente

> **⚠️ Importante:** `GI_G_EXOGENA_RETENCIONES` almacena retenciones **municipales de ICA**, NO exógena de la DIAN (que es de Renta/IVA). Las retenciones de ICA son municipales. El código interno usa el nombre `exogena_dian` por razones históricas, pero la fuente es municipal.

### PostgreSQL (Base del sistema FiscalIA)
- **procesos**: Procesos de fiscalización creados
- **proceso_detalle**: Resultados del análisis por NIT
- **hallazgos_fiscales**: Hallazgos detectados y su estado de revisión
- **entidades_fiscalizadoras**: Municipios o entidades usando el sistema

### PostgreSQL (Base del sistema FiscalIA)
- **procesos**: Procesos de fiscalización creados
- **proceso_detalle**: Resultados del análisis por NIT
- **hallazgos_fiscales**: Hallazgos detectados y su estado de revisión
- **entidades_fiscalizadoras**: Municipios o entidades usando el sistema

---

## 3. Clasificación de Contribuyentes

### 3.1. OMISO

Un contribuyente es **OMISO** cuando está obligado a declarar ICA pero no presentó declaración en el período analizado.

**Cómo se detecta:**
- El sistema busca contribuyentes registrados en el padrón municipal que no tienen declaraciones ICA en el período
- También detecta contribuyentes reportados por DIAN (exógena) que no aparecen en el registro municipal

**Subtipos:**
| Subtipo | Descripción |
|---|---|
| OMISO CONOCIDO | Registrado en el municipio pero sin declarar |
| OMISO DESCONOCIDO | Detectado por DIAN, no existe en el padrón municipal |

### 3.2. EXACTO

Un contribuyente es **EXACTO** cuando sus declaraciones ICA coinciden razonablemente con la información de terceros (exógena DIAN, retenciones).

### 3.3. INEXACTO

Un contribuyente es **INEXACTO** cuando hay diferencias significativas entre lo declarado y lo reportado por terceros. Por ejemplo:

- El CIIU que declaró no coincide con el que reporta DIAN
- Las retenciones declaradas difieren de las reportadas en exógena
- Hay diferencias significativas entre ingresos reportados por terceros y base gravable declarada

---

## 4. Sistema de Riesgo Fiscal (SRF)

El SRF asigna un puntaje de 0 a 100 basado en 4 componentes:

| Componente | Peso | ¿Qué mide? |
|---|---|---|
| Diferencia exógena vs ICA | **35 pts** | Qué tanto difieren los ingresos reportados por terceros (exógena retenciones, base `VLOR_BSE` filtrado RD) vs lo declarado (`BSE_GRVBLE`) |
| Antigüedad sin declarar | **20 pts** | Cuántos períodos lleva sin declarar (de los últimos 6) |
| Discrepancia de tarifa | **25 pts** | Si la tarifa aplicada difiere de la tarifa oficial del CIIU |

> **Nota técnica:** Las tarifas oficiales del CIIU se cargan desde las declaraciones ICA en Oracle (`GI_G_DECLARACIONES_DETALLE` con atributos 2107/4371/4874) al iniciar el servicio (`cargar_tarifas_desde_oracle()`). Se toma la tarifa más frecuente por CIIU del período. Si no hay datos en Oracle para un CIIU, se usa el mapa por defecto `TARIFAS_CIIU_DEFAULT` (8 códigos: 4711, 4712, 4721, 5611, 6820, 8511, 6201, 6202).
| Estado RUES vs padrón | **20 pts** | Si el contribuyente está inactivo/suspendido en el RUES |

**Nivel de riesgo según puntaje:**

| SRF | Nivel |
|---|---|
| 70 - 100 | ALTO |
| 40 - 69 | MEDIO |
| 0 - 39 | BAJO |

---

## 5. Análisis Comportamental

Compara al contribuyente contra su **grupo de pares**: otros contribuyentes del mismo CIIU, mismo régimen y mismo año.

### 5.1. ¿Cómo funciona?

1. Se obtienen todos los contribuyentes con el mismo CIIU (hasta 2,000)
2. Se calculan estadísticos del grupo: mediana, percentiles (10, 25, 75, 90)
3. Se compara el contribuyente individual contra el grupo

### 5.2. Indicadores detectados

| Situación detectada | Severidad |
|---|---|
| Base gravable está en el 10% más bajo del sector | ALTA |
| Base gravable está en el 25% más bajo del sector | MEDIA |
| Base gravable cayó más del 70% vs la mediana del sector | ALTA |
| Base gravable cayó más del 50% vs la mediana del sector | MEDIA |
| Declaró base cero pero tiene ingresos reportados por terceros | ALTA |
| Ingresos de terceros duplican o triplican lo declarado | ALTA / MEDIA |
| Tarifa efectiva está por debajo de la mitad de lo normal en su sector | MEDIA |
| Es un outlier estadístico muy por debajo del grupo | MEDIA |

### 5.3. Confianza del análisis

| Cantidad de pares | Confianza |
|---|---|
| 100 o más | 90% |
| 30 - 99 | 75% |
| 10 - 29 | 60% |
| Menos de 10 | 40% (poco representativo) |

### 5.4. Prioridad del score comportamental

| Score | Prioridad |
|---|---|
| 80 - 100 | ALTA |
| 55 - 79 | MEDIA |
| 0 - 54 | BAJA |

---

## 6. Reglas Fiscales (R1 a R10)

Cada regla representa un **patrón de riesgo** fiscal. Se clasifican por su **fuerza probatoria**:

| Fuerza | Significado |
|---|---|
| **DIRECTA** | Prueba contundente, poco margen de error |
| **MEDIA** | Evidencia sólida pero requiere contexto |
| **INDICIARIA** | Señal estadística, requiere corroboración |

---

### 6.1. Estado de Implementación

| Regla | Nombre | Fuerza | Estado | Fuente de datos | Por qué falta / qué se necesita |
|---|---|---|---|---|---|
| **R1** | Retención sin declaración suficiente | DIRECTA | ✅ **Operativa** | Oracle: retenciones declaradas + exógena | Se implementó recientemente. `retenciones_ica` se construye desde `retenciones_declaradas_practicadas` y `retenciones_exogena_practicadas`. |
| **R2** | Omiso con presencia registral | DIRECTA | ✅ **Operativa** | Oracle: `DF_S_SUJETOS_ESTADO` | Se implementó recientemente. `rues_estado` ahora se decodifica correctamente (ACTIVO/INACTIVO/OMISO_DESCONOCIDO) desde Oracle. |
| **R3** | Brecha exógena ICA | DIRECTA | ✅ **Operativa** | Oracle: `GI_G_EXOGENA_RETENCIONES` (filtrando RD) + `GI_G_DECLARACIONES` | Compara `VLOR_BSE` (base de retención recibida) vs `BSE_GRVBLE` (base declarada). Fix 2026-07-23: se corrigió `vlor_rtncion` → `vlor_bse` y se agregó filtro `cdgo_exgna_tpo_rgstro = 'RD'`. |
| **R4** | Brecha facturación electrónica | DIRECTA | 🟡 **Fuente identificada** | Oracle: `GI_G_INTERMEDIA_DIAN` / `GI_G_EXOGENA_INGR_FRA_MUNI` | **Sí se puede implementar.** El motor existe. Se identificaron dos fuentes de datos en Oracle: `GI_G_INTERMEDIA_DIAN.TTAL_INGRSOS_GRVBLE` (ingresos gravables ICA por contribuyente) y `GI_G_EXOGENA_INGR_FRA_MUNI` (ingresos facturación municipal agregados). Falta agregar la query y mapeo al perfil fiscal. |
| **R5** | Contratista estatal no declarante | DIRECTA | 🔴 **No implementada — posible** | Nueva fuente: contratos SECOP | **Sí se puede implementar**, pero no existe query que traiga contratos públicos. SECOP tiene API pública, o podría cargarse desde una tabla Oracle si el municipio la replica. |
| **R6** | Declarante en cero persistente | INDICIARIA | ✅ **Operativa** | Oracle: `GI_G_DECLARACIONES` | Funciona. Detecta ceros repetidos con señales de actividad. |
| **R7** | CIIU conveniente | MEDIA | ✅ **Operativa** | Oracle: tarifas desde `GI_G_DECLARACIONES_DETALLE` | Se implementó recientemente. `tarifa_correcta` se obtiene de `_tarifas_ciiu` (cargado al startup desde Oracle). |
| **R8** | Atípico sectorial | INDICIARIA | 🔴 **No implementada — requiere diseño** | Motor acumulativo por CIIU | **Requiere diseño nuevo**: necesita percentiles sectoriales que se construyen a medida que el módulo analiza contribuyentes (no es una query puntual). Cada análisis alimenta un acumulador por CIIU que mejora su precisión con el tiempo. |
| **R9** | Territorialidad | MEDIA | ✅ **Operativa** | Oracle: `GI_G_EXOGENA_RETENCIONES` + `GI_G_DECLARACIONES` | **Implementada recientemente.** Calcula `max(total_exógena - total_base_declarada, 0)` desde datos existentes. Sin queries nuevas. |
| **R10** | Caída abrupta de base | INDICIARIA | ✅ **Operativa** | Oracle: `GI_G_DECLARACIONES` (histórico) | Funciona con histórico de declaraciones (mínimo 2 períodos). |

**Leyenda:**
- ✅ Operativa = se ejecuta correctamente en producción con datos reales
- 🔴 No implementada — posible = el motor de reglas está escrito pero nunca se ejecuta porque el perfil no recibe los datos necesarios. La fuente de datos existe o puede integrarse.
- 🔴 No implementada — requiere diseño = no es una query directa, necesita un componente nuevo (acumulador/agregador)

### Regla R1 — Retención sin declaración suficiente
- **Fuerza:** DIRECTA | **Estado:** ✅ Operativa
- **Qué detecta:** Contribuyentes a los que le retuvieron ICA pero no declararon lo suficiente para cubrir esas retenciones
- **Qué necesita:** Datos de retenciones ICA desde declaraciones y exógena Oracle
- **Origen:** `retenciones_declaradas_practicadas` (declaraciones) y `retenciones_exogena_practicadas` (exógena DIAN)
- **Resultado:** OMISO (si no declaró) o INEXACTO (si declaró menos de lo esperado)

### Regla R2 — Omiso con presencia registral
- **Fuerza:** DIRECTA | **Estado:** ✅ Operativa
- **Qué detecta:** Contribuyentes registrados en el sistema municipal (activos en el padrón) pero que no declaran ICA
- **Qué necesita:** Estado registral (`DF_S_SUJETOS_ESTADO`: A=ACTIVO, I=INACTIVO, O=OMISO_DESCONOCIDO)
- **Origen:** Oracle `DF_S_SUJETOS_ESTADO.cdgo_sjto_estdo` decodificado con CASE
- **Resultado:** OMISO

### Regla R3 — Brecha exógena ICA
- **Fuerza:** DIRECTA | **Estado:** ✅ Operativa (fix 2026-07-23)
- **Qué detecta:** Ingresos reportados por terceros (exógena municipal de retenciones) superan significativamente la base gravable declarada
- **Qué necesita:** Datos de exógena municipal de retenciones ICA, declaraciones ICA
- **Origen:** `GI_G_EXOGENA_RETENCIONES`. Usa exclusivamente registros `cdgo_exgna_tpo_rgstro = 'RD'` (retenciones recibidas = le retuvieron al contribuyente), pues esos reflejan sus ingresos. Los registros `'RP'` (retenciones practicadas = él retuvo a otros) no son relevantes para R3.
- **Columna usada:** `VLOR_BSE` (base de la operación). Ya NO usa `VLOR_RTNCION` (valor de retención).
- **Resultado:** OMISO (si no declaró) o INEXACTO (si la diferencia supera el umbral del 15%)

> **⚠️ Fix 2026-07-23:** Originalmente R3 usaba `SUM(vlor_rtncion)` — que suma el valor de la retención, no la base. Esto hacía que los valores fueran ~100x menores a la base declarada, y R3 nunca superaba el umbral del 15%. Se corrigió a `SUM(vlor_bse)` (base real de cada operación de retención, ej: $8M en vez de $40k). También se corrigió un bug en `pagination.py` donde los CASE `'RECIBIDA'/'PRACTICADA'` nunca matcheaban porque los valores reales son `'RD'/'RP'`. Ver `tests/unit/test_exogena_fix.py` para los tests de regresión.

### Regla R4 — Brecha facturación electrónica
- **Fuerza:** DIRECTA | **Estado:** 🟡 Fuente identificada
- **Qué detecta:** Facturación electrónica local es mayor a la base gravable declarada
- **Qué necesita:** Datos de ingresos gravables ICA desde DIAN, declaraciones ICA
- **Fuentes identificadas en Oracle:**
  - `GI_G_INTERMEDIA_DIAN.TTAL_INGRSOS_GRVBLE` — ingresos gravables ICA reportados a DIAN, por contribuyente y período
  - `GI_G_EXOGENA_INGR_FRA_MUNI` — ingresos de facturación municipal agregados (por municipio, habría que ligar por contribuyente vía `SI_I_SUJETOS_IMPUESTO`)
- **Por qué falta:** El motor de reglas (`_evaluar_r4`) existe y está escrito, pero `facturacion_electronica` nunca se setea en el perfil fiscal. Las tablas existen en Oracle, solo falta agregar la query + mapeo.
- **Resultado:** OMISO o INEXACTO

### Regla R5 — Contratista estatal no declarante
- **Fuerza:** DIRECTA | **Estado:** 🔴 No implementada — **posible**
- **Qué detecta:** Empresas con contratos públicos que no declaran ICA o declaran menos de lo que facturaron al Estado
- **Qué necesita:** Datos de contratación pública (SECOP), declaraciones ICA
- **Por qué falta:** El motor de reglas (`_evaluar_r5`) existe y está escrito, pero `contratos_publicos` nunca se setea en el perfil fiscal. No hay query que integre SECOP.
- **Qué se necesita:** Integrar datos de contratación pública (API SECOP, o tabla Oracle si el municipio la replica) y agregar la query + mapeo al perfil.
- **Resultado:** OMISO o INEXACTO

### Regla R6 — Declarante en cero persistente
- **Fuerza:** INDICIARIA | **Estado:** ✅ Operativa
- **Qué detecta:** Contribuyentes que declaran base cero repetidamente pero tienen señales de actividad
- **Qué necesita:** Histórico de declaraciones en cero, señales de actividad económica
- **Resultado:** INEXACTO (indiciario)

### Regla R7 — CIIU conveniente
- **Fuerza:** MEDIA | **Estado:** ✅ Operativa
- **Qué detecta:** Contribuyentes que declaran una actividad económica con tarifa menor a la que realmente les corresponde
- **Qué necesita:** CIIU de DIAN vs CIIU declarado, tarifas oficiales desde Oracle
- **Origen:** Tarifas cargadas al startup desde `GI_G_DECLARACIONES_DETALLE` (atributos 2107/4371/4874)
- **Resultado:** INEXACTO, con impuesto estimado calculado

### Regla R8 — Atípico sectorial
- **Fuerza:** INDICIARIA | **Estado:** 🔴 No implementada — **requiere diseño nuevo**
- **Qué detecta:** Contribuyentes con comportamiento atípico comparado con su sector (múltiples indicadores en percentiles extremos)
- **Qué necesita:** Comparación estadística contra pares del mismo CIIU
- **Por qué falta:** No es una query puntual a Oracle. Necesita un **motor acumulativo** que construya percentiles sectoriales a medida que el módulo analiza contribuyentes. Cada análisis alimenta un acumulador por CIIU que mejora su precisión con el tiempo de uso.
- **Qué se necesita:** Diseñar e implementar el acumulador sectorial (en memoria o PostgreSQL) que recolecte bases gravables por CIIU y compute percentiles 10/25/50/75/90.
- **Resultado:** INEXACTO (indiciario)

### Regla R9 — Territorialidad
- **Fuerza:** MEDIA | **Estado:** ✅ **Operativa**
- **Qué detecta:** Ingresos generados en el municipio que se declararon (o no) localmente vs reportados a DIAN
- **Qué necesita:** Datos de exógena DIAN, declaraciones ICA
- **Origen:** Calcula `ingresos_locales_no_declarados = max(total_exógena_ingresos - total_base_declarada, 0)` desde datos existentes. Sin queries nuevas.
- **Resultado:** INEXACTO

### Regla R10 — Caída abrupta de base
- **Fuerza:** INDICIARIA | **Estado:** ✅ Operativa
- **Qué detecta:** Caídas interanuales de base gravable superiores al 60%
- **Qué necesita:** Histórico de declaraciones de al menos 2 períodos
- **Resultado:** INEXACTO (indiciario)

---

## 7. Patrones Temporales

Se analiza el **historial completo** del contribuyente (todos los períodos disponibles) para detectar:

| Patrón | Severidad | ¿Qué detecta? |
|---|---|---|
| Caída abrupta | ALTA | Base gravable cayó más del 60% respecto al año anterior |
| Tendencia descendente | ALTA/MEDIA | La base ha venido bajando durante 3 o más años consecutivos |
| Divergencia exógena creciente | ALTA/MEDIA | La exógena crece pero la base gravable no (o baja) |
| Volatilidad sospechosa | MEDIA | La base gravable varía drásticamente de un año a otro |
| Desaparición declarativa | ALTA | El contribuyente declaraba y dejó de hacerlo |

---

## 8. Score Unificado

> **Nota:** El score unificado solo se calcula en procesos de tipo COMPLETO. En procesos BASICO solo se calcula SRF + explicación LLM.

El **score final** (0 a 100) combina todos los análisis:

| Componente | Peso |
|---|---|
| Score comportamental (vs pares) | 30% |
| Score SRF (cruce exógena vs ICA) | 20% |
| Score reglas fiscales (R1-R10) | 20% |
| Score de red (conexiones con otros contribuyentes) | 15% |
| Score temporal (patrones históricos) | 10% |
| Confianza del análisis | 5% |

**Prioridad final:**

| Score | Prioridad | Acción sugerida |
|---|---|---|
| 90 - 100 | **CRÍTICA** | Revisión prioritaria inmediata |
| 75 - 89 | **ALTA** | Pasar a revisión humana |
| 50 - 74 | **MEDIA** | Revisar en cola normal |
| 0 - 49 | **BAJA** | Mantener en monitoreo |

---

## 9. Hallazgos

### 9.1. ¿Qué es un hallazgo?

Es una anomalía o inconsistencia detectada durante el análisis. Cada hallazgo tiene:

- **Tipo**: OMISO, INEXACTO, TARIFA_INCORRECTA, etc.
- **Severidad**: ALTA, MEDIA, BAJA
- **Fuerza probatoria**: DIRECTA, MEDIA, INDICIARIA
- **Descripción**: texto explicativo del hallazgo
- **Evidencia**: datos concretos que respaldan el hallazgo

### 9.2. Scoring de hallazgos

Cada hallazgo recibe un puntaje (0-100) basado en:

| Factor | Peso |
|---|---|
| Fuerza probatoria | 35% |
| Monto del impuesto estimado | 30% |
| Urgencia (qué tan cerca está de prescribir) | 15% |
| Reincidencia del contribuyente | 10% |
| Corroboración por múltiples fuentes | 10% |

**Bandas de prioridad:** A (>=80), B (>=60), C (>=40), D (<40)

### 9.3. Ciclo de vida del hallazgo

```
DETECTADO → REVISIÓN HUMANA (HITL) → CONFIRMADO / DESCARTADO / RECLASIFICADO
```

1. **Detección**: El sistema encuentra una anomalía y crea el hallazgo
2. **Revisión humana (HITL)**: Un fiscalizador revisa, comenta y decide (CONFIRMAR / DESCARTAR / RECLASIFICAR)
3. **Resolución**: Aprobado (pasa a acción fiscal) o descartado (evidencia insuficiente)

### 9.4. Revisión de calidad (automática)

Antes de pasar a revisión humana, el sistema evalúa:

| Verificación | ¿Qué pasa si falla? |
|---|---|
| ¿Tiene suficientes evidencias? | Se marca como incompleto |
| ¿Es accionable (ventana legal vigente)? | Se marca como no accionable |
| ¿Tiene brecha o impuesto calculado? | Se pide cuantificar |
| ¿Tiene resumen explicativo? | Se genera uno automáticamente |

---

## 10. Proceso Completo: Ejemplo Real

Un proceso de fiscalización con 100 contribuyentes del CIIU 3693:

1. **Inicio**: Funcionario crea proceso para CIIU 3693, período 2024, 100 NITs
2. **Pre-filtro**: Oracle encuentra 873 contribuyentes de ese CIIU; toma los primeros 100
3. **Clasificación**: El sistema determina la situación de cada uno (OMISO/EXACTO/INEXACTO)
4. **Análisis por NIT**: Por cada contribuyente, se ejecutan SRF + score comportamental + reglas fiscales
5. **Resultado**: Score unificado, hallazgos detectados, nivel de riesgo
6. **Persistencia**: Todo se guarda en PostgreSQL para consulta del funcionario
7. **Revisión**: Los hallazgos pasan a revisión humana para decisión final

> **Tiempo estimado**: ~16 minutos para 100 NITs (con LLM incluido)

---

*Documento generado el 16/07/2026 — Sistema FiscalIA v2.0.0*

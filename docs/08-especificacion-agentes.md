# Especificación de Agentes — FiscalIA

> Basado en la metodología **AI-DLC Hat-Based** y el PRD v2.0 de FiscalIA.

## 1. AGT-00: Orchestrator

**Responsabilidad:** Coordina el flujo entre agentes, gestiona expedientes, maneja HITL y la cola de trabajo del fiscalizador.

**Implementación:** PL/SQL Package `FISCAL_ORCH` + Oracle APEX (dashboard).

**Input:** Campaña de fiscalización.
**Output:** Expedientes creados, flujo de análisis orquestado.

**Relación con el microservicio:** El microservicio NO implementa AGT-00. Es responsabilidad del equipo APEX/PL-SQL.

---

## 2. AGT-01: CrossCheck Agent

**Responsabilidad:** Cruza información del contribuyente contra múltiples fuentes: exógena DIAN, RUES/Confecámaras y padrón ICA. Calcula los componentes base del Score de Riesgo Fiscal (SRF).

### Alcance del Microservicio

El microservicio **consume** los resultados de AGT-01 a través de:

- `FISCAL_CROSS.obtener_cruces(nit, periodo)` → Lista de cruces exógena vs ICA
- `FISCAL_CROSS.obtener_srf_base(nit, periodo)` → SRF base sin explicación

### Input (PL/SQL)

| Dato | Fuente |
|---|---|
| NIT del contribuyente | Tabla contribuyentes |
| Ingresos declarados ICA | Tabla declaraciones_ica |
| Ingresos reportados exógena | Tabla exogena (importada) |
| Estado RUES | Web service RUES |
| Tarifas CIIU vigentes | Tabla paramétrica municipal |

### Output (cursor PL/SQL)

```json
{
  "ciiu": "4711",
  "ingreso_declarado": 50000000,
  "ingreso_exogena": 120000000,
  "diferencia": 70000000,
  "variacion_pct": 140,
  "umbral_superado": 1
}
```

---

## 3. AGT-02: OmisosDetect

**Responsabilidad:** Detecta contribuyentes que no presentan declaraciones ICA en los períodos fiscalizables.

**Implementación:** PL/SQL (queries directas + UTL_MATCH para fuzzy matching).

**NO requiere microservicio.** No hay llamada a IA para esta función en V1.

### Métodos de detección

1. **Histórico:** Contribuyentes que declaraban y dejaron de hacerlo (2+ períodos)
2. **RUES:** Empresas activas en RUES sin registro en padrón ICA
3. **Fuzzy matching:** UTL_MATCH.JARO_WINKLER_SIMILARITY para detectar mismos contribuyentes con nombres ligeramente distintos

---

## 4. AGT-03: InconsistencyAnalyzer

**Responsabilidad:** Analiza declaraciones ICA para detectar inconsistencias: subdeclaración, tarifa incorrecta, período incorrecto, base cero, exenciones indebidas.

### Alcance del Microservicio

El microservicio:
1. **Consume** `FISCAL_INC.obtener_inconsistencias(nit, periodo)` — lista de inconsistencias detectadas por PL/SQL
2. **Enriquece** con IA: genera explicación en lenguaje natural y recomendación de acción vía LLM

### Tipos de Inconsistencia

| Tipo | Código | Descripción |
|---|---|---|
| Subregistro de ingresos | `SUBREGISTRO` | Exógena reporta más ingresos que ICA |
| Tarifa incorrecta | `TARIFA` | Tarifa aplicada no corresponde a la vigente |
| Período incorrecto | `PERIODO` | Mezcla bimestres como anuales |
| Exención indebida | `EXENCION` | Aplica exención sin soporte documental |
| Base cero injustificada | `BASE_CERO` | Base gravable cero sin estado de inactividad |
| Otra | `OTRA` | No clasificada en los tipos anteriores |

### Output del Microservicio

Por cada inconsistencia, el microservicio retorna:
- Tipo y severidad
- Valores (declarado, referencia, diferencia)
- **Explicación IA** en lenguaje natural para el funcionario
- **Recomendación de acción** (ej: "Verificar con el contribuyente la diferencia de $70M en CIIU 4711")

---

## 5. AGT-04: LegalDraft (DIFERIDO)

**Responsabilidad:** Generación de Requerimientos Ordinarios, Emplazamientos para Declarar y Autos de Inspección.

**Estado:** **DIFERIDO** — No incluido en V1. Requiere RAG normativo (Oracle AI Vector Search) y validación jurídica.

**Versión objetivo:** SaaS v1.0 (Next AI Tech LLC).

---

## 6. Matriz de Responsabilidades

| Agente | PL/SQL | APEX | Microservicio Python | Claude API |
|---|---|---|---|---|
| AGT-00 Orchestrator | ✅ | ✅ | ❌ | ❌ |
| AGT-01 CrossCheck | ✅ | ❌ | ✅ (consumir) | ✅ (explicación SRF) |
| AGT-02 OmisosDetect | ✅ | ✅ | ❌ | ❌ |
| AGT-03 InconsistencyAnalyzer | ✅ | ❌ | ✅ (consumir + enriquecer) | ✅ (explicación hallazgos) |
| AGT-04 LegalDraft | ❌ | ❌ | ❌ | ❌ (diferido) |

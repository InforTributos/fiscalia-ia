# Especificación de Agentes — FiscalIA

> Basado en la metodología **AI-DLC Hat-Based** y el PRD v2.0 de FiscalIA.

## 1. AGT-00: Orchestrator

**Responsabilidad:** Coordina el flujo entre agentes, gestiona la creación de procesos, background tasks y la cola de trabajo.

**Implementación:** `tasks/analisis_task.py` + `application/use_cases/orquestar_proceso.py`

**Input:** Criterios de fiscalización (vigencia, régimen, CIIU, período).
**Output:** Proceso creado con análisis IA en background.

**Relación con el microservicio:** El microservicio implementa AGT-00 vía `asyncio.create_task()`. El proceso se lanza desde `POST /proceso`.

---

## 2. AGT-01: CrossCheck Agent

**Responsabilidad:** Cruza información del contribuyente contra múltiples fuentes: exógena DIAN, RUES/Confecámaras y padrón ICA. Calcula los componentes base del Score de Riesgo Fiscal (SRF).

### Implementación

| Componente | Archivo |
|---|---|
| Cálculo SRF (4 componentes) | `domain/services/crosscheck_service.py` — `calcular_srf()` |
| Clasificación (omiso/exacto/inexacto) | `domain/services/crosscheck_service.py` — `clasificar_por_datos()` |
| Extracción de inconsistencias | `domain/services/crosscheck_service.py` — `extraer_inconsistencias()` |
| Nivel de riesgo | `domain/services/inconsistency_service.py` — `nivel_riesgo()` |

### Input

| Dato | Fuente |
|---|---|
| NIT del contribuyente | MCP Server vía `obtener_datos_fiscales` |
| Ingresos declarados ICA | MCP Server (declaraciones_ica) |
| Ingresos reportados exógena | MCP Server (exogena_dian) |
| Estado RUES | MCP Server (rues_estado) |
| Tarifas CIIU vigentes | `crosscheck_service.py` — `TARIFAS_CIIU` (provisional) |

### Output

```json
{
  "srf_total": 78.5,
  "componentes_srf": {
    "diferencia_exogena": { "peso": 35, "valor": 28 },
    "antiguedad_omision": { "peso": 20, "valor": 15 },
    "discrepancia_tarifa_ciiu": { "peso": 25, "valor": 20 },
    "estado_rues": { "peso": 20, "valor": 15 }
  },
  "nivel_riesgo": "ALTO"
}
```

---

## 3. AGT-02: OmisosDetect

**Responsabilidad:** Detecta contribuyentes que no presentan declaraciones ICA en los períodos fiscalizables.

**Implementación:** `domain/services/crosscheck_service.py` — `clasificar_por_datos()`

**Métodos de detección:**

1. **Histórico:** Contribuyentes con declaraciones ICA vacías (`declaraciones_ica: []`)
2. **RUES vs padrón:** Empresas activas en RUES sin registro de declaraciones ICA
3. **Clasificación:** Si no hay declaraciones → `OMISO`

---

## 4. AGT-03: InconsistencyAnalyzer

**Responsabilidad:** Analiza declaraciones ICA para detectar inconsistencias: subdeclaración, tarifa incorrecta, base cero, exenciones indebidas.

### Implementación

- `domain/services/crosscheck_service.py` — `extraer_inconsistencias()` para detectar anomalías
- `domain/services/inconsistency_service.py` — `nivel_riesgo()` para asignar nivel
- `infrastructure/llm/llm_service.py` — LLM genera explicación en lenguaje natural

### Tipos de Inconsistencia

| Tipo | Código | Descripción |
|---|---|---|
| Subregistro de ingresos | `SUBDECLARACION_EXOGENA` | Exógena reporta más ingresos que ICA |
| Tarifa incorrecta | `TARIFA_INCORRECTA` | Tarifa aplicada no corresponde a la vigente |
| Período incorrecto | `PERIODO_INCORRECTO` | Mezcla bimestres como anuales |
| Exención indebida | `EXENCION_IMPROCEDENTE` | Aplica exención sin soporte documental |
| Base cero injustificada | `BASE_CERO` | Base gravable cero sin estado de inactividad |

### Output del Microservicio

Por cada inconsistencia, el microservicio retorna:
- Tipo y severidad
- Valores (declarado, referencia, diferencia)
- **Explicación IA** en lenguaje natural para el funcionario
- **Recomendación de acción**

---

## 5. AGT-04: LegalDraft (DIFERIDO)

**Responsabilidad:** Generación de Requerimientos Ordinarios, Emplazamientos para Declarar y Autos de Inspección.

**Estado:** **DIFERIDO** — No incluido en V1. Requiere RAG normativo y validación jurídica.

---

## 6. AGT-05: MCP Client

**Responsabilidad:** Gestiona la conexión stdio con el MCP Server, paginación de resultados y filtrado de candidatos.

**Implementación:** `infrastructure/mcp/oracle_adapter.py` + `pagination.py` + `classify.py`

| Componente | Archivo |
|---|---|
| Cliente MCP stdio | `infrastructure/mcp/oracle_adapter.py` — `MCPClient` |
| Paginación automática | `infrastructure/mcp/pagination.py` — `obtener_datos_fiscales()` |
| Clasificación de candidatos | `infrastructure/mcp/classify.py` |

**MCP Tools consumidas:**

| Tool | Propósito |
|---|---|
| `buscar_contribuyentes` | Obtener NITs candidatos con score/razón |
| `obtener_datos_fiscales` | Datos fiscales completos por NIT |

---

## 7. Matriz de Responsabilidades

| Agente | Microservicio | LLM Provider | MCP Server |
|---|---|---|---|
| AGT-00 Orchestrator | ✅ | ❌ | ❌ |
| AGT-01 CrossCheck | ✅ | ✅ (explicación SRF) | ✅ (datos) |
| AGT-02 OmisosDetect | ✅ | ❌ | ✅ (datos) |
| AGT-03 InconsistencyAnalyzer | ✅ | ✅ (explicación hallazgos) | ✅ (datos) |
| AGT-04 LegalDraft | ❌ (diferido) | ❌ | ❌ |
| AGT-05 MCP Client | ✅ | ❌ | ✅ (gestión conexión) |

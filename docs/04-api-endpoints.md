# API Endpoints — FiscalIA

## 1. POST /proceso — Crear proceso asíncrono

**Request:**

```json
{
  "entidad_nit": "9003189639",
  "nombre": "Proceso Comercio Q1 2024",
  "vigencia_ini": "2024-01-01",
  "vigencia_fin": "2024-12-31",
  "tipo_regimen": "COMUN",
  "actividades_economicas": ["4711", "4712", "4721"],
  "periodo": "2024",
  "tipo": "COMPLETO",
  "max_nits": 0,
  "umbral_retenciones_pct": 5.0
}
```

| Parámetro | Tipo | Default | Requerido | Descripción |
|---|---|---|---|---|
| `entidad_nit` | string | — | Sí | NIT de la entidad fiscalizadora |
| `nombre` | string | — | Sí | Nombre descriptivo del proceso |
| `vigencia_ini` | string | — | Sí | Fecha inicial del período (YYYY-MM-DD) |
| `vigencia_fin` | string | — | Sí | Fecha final del período (YYYY-MM-DD) |
| `tipo_regimen` | string | — | Sí | COMUN / SIMPLIFICADO |
| `actividades_economicas` | string[] | — | Sí | Lista de códigos CIIU |
| `periodo` | string | — | Sí | Año fiscal |
| `tipo` | string | `BASICO` | No | `BASICO` = SRF+LLM (paralelo), `COMPLETO` = BASICO + comportamiento + reglas + score + resumen |
| `max_nits` | int | 0 | No | Límite de NITs a procesar (0 = ilimitado) |
| `umbral_retenciones_pct` | float | 5.0 | No | Umbral porcentual para inexactos retenciones |

**Response (201):**

```json
{
  "proceso_id": "uuid-del-proceso",
  "intento_id": 1,
  "estado": "EN_COLA",
  "nombre": "Proceso Comercio Q1 2024",
  "entidad_nit": "9003189639",
  "resumen": {
    "total_nits": 0,
    "omisos": 0,
    "exactos": 0,
    "inexactos": 0
  },
  "proceso_analisis": {
    "estado": "EN_COLA",
    "mensaje": "Proceso creado. Iniciando pre-filtrado de candidatos en Oracle."
  },
  "created_at": "2026-06-21T10:30:00Z"
}
```

**Re-lanzamiento:** Si se envía el mismo `entidad_nit` + mismos `criteria`, se detecta como re-lanzamiento y se crea un nuevo `proceso_intentos` con `numero_intento` incremental.

**Lógica de re-lanzamiento:**

| Aspecto | Comportamiento |
|---|---|
| Detección | Comparación de `entidad_nit` + hash de `criteria` (JSON deep equality) |
| Si hay proceso `EN_PROCESO` con mismos criteria | Se rechaza con 409 `PROCESO_EN_PROCESO` |
| Si hay proceso `COMPLETADO`/`ERROR` con mismos criteria | Se crea nuevo intento con `numero_intento` incremental |
| Resultados anteriores | Se preservan (historial de intentos) |
| Re-solo NITs fallidos | **No soportado en V1** — se re-ejecutan todos |

**Cancelación:** Endpoint `POST /proceso/{proceso_id}/cancelar` disponible. Marca el proceso como `INTERRUMPIDO` y cancela la tarea activa via `asyncio.CancelledError`.

**Flujo interno:**

1. `POST /proceso` recibe el request, valida que la entidad exista en PostgreSQL, verifica duplicados activos (mismos criteria), crea el proceso + intento en PostgreSQL, actualiza estado a `EN_COLA`, dispara `asyncio.create_task()` en background, retorna **201** inmediato con `ProcesoResumen()` vacío (todo en cero).

2. **Background task** (`_lanzar_analisis` → `analizar_proceso`):
   - Espera turno en semáforo de concurrencia (max 5 procesos simultáneos)
   - **Pre-filtro Oracle**: ejecuta 4 queries de descubrimiento (omisos conocidos, omisos desconocidos, inexactos CIIU, inexactos retenciones) → clasifica contribuyentes como `OMISO` o `INEXACTO`
   - **Análisis IA por NIT**: para cada NIT ejecuta SRF (cálculo local) + LLM (cadena de 3 tiers con fallback)
   - **Si es COMPLETO**: además corre análisis comportamental (grupo par), reglas fiscales, genera score unificado y expediente fiscal

---

## 2. GET /proceso/{id}/status — Consultar estado

**Response (200):**

```json
{
  "proceso_id": "uuid-del-proceso",
  "estado": "EN_PROCESO",
  "entidad_nit": "9003189639",
  "intento_actual": {
    "numero": 2,
    "estado": "EN_PROCESO",
    "procesados": 995,
    "errores": 3
  },
  "intentos_historial": [
    { "numero": 1, "estado": "ERROR", "errores_count": 12, "started_at": "2026-06-20T10:00:00Z" },
    { "numero": 2, "estado": "EN_PROCESO", "errores_count": 3, "started_at": "2026-06-21T10:30:05Z" }
  ],
  "progreso": {
    "porcentaje": 45.2,
    "total_nits": 2200,
    "procesados": 995,
    "faltantes": 1205
  },
  "clasificacion": {
    "omisos": { "total": 1200, "procesados": 0 },
    "inexactos": { "total": 1000, "procesados": 0 }
  },
  "started_at": "2026-06-21T10:30:05Z",
  "ultimo_update": "2026-06-21T10:35:12Z"
}
```

**Estados posibles:**

| Estado | Significado |
|---|---|
| `PENDIENTE` | Proceso creado, esperando ejecución |
| `PREFILTRANDO` | MCP está obteniendo NITs |
| `PREFILTRADO_COMPLETADO` | NITs clasificados, análisis IA en cola |
| `EN_COLA` | Esperando worker disponible |
| `EN_PROCESO` | Análisis IA en ejecución |
| `COMPLETADO` | Todos los NITs analizados |
| `INTERRUMPIDO` | Contenedor reiniciado mid-process (recuperable) |
| `ERROR` | Error en el proceso (detalle en proceso_errores) |

**Máquina de estados:**

```
PENDIENTE → PREFILTRANDO → PREFILTRADO_COMPLETADO → EN_COLA → EN_PROCESO → COMPLETADO | ERROR
```

---

## 3. GET /proceso/{id}/results — Consultar resultados

**Query parameters:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `page` | int | 1 | Número de página |
| `page_size` | int | 50 | Registros por página (max 500) |
| `intento_id` | int | null | Filtrar por intento específico (si null, usa el último intento) |
| `include_partial` | boolean | false | Si true, retorna resultados parciales aunque el proceso no haya terminado |
| `clasificacion` | string | null | Filtro: `OMISO`, `EXACTO`, `INEXACTO` |
| `min_score` | float | null | Filtrar por score mínimo del MCP |
| `ordenar_por` | string | `mcp_score` | Campo de ordenamiento: `mcp_score`, `nit`, `created_at` |
| `direccion` | string | `desc` | `asc` o `desc` |

**Response (200) — Proceso completado:**

```json
{
  "proceso_id": "uuid-del-proceso",
  "estado": "COMPLETADO",
  "intento_id": 2,
  "parcial": false,
  "paginacion": {
    "page": 1,
    "page_size": 50,
    "total_registros": 2200,
    "total_paginas": 44
  },
  "resultados": [
    {
      "contribuyente_nit": "9003189639",
      "razon_social": "COMERCIO XYZ S.A.S.",
      "ciiu": "4711",
      "clasificacion": "INEXACTO",
      "mcp_score": 85.5,
      "mcp_razon": "Diferencia de ingresos del 45%",
      "srf_total": 78,
      "nivel_riesgo": "ALTO",
      "hallazgos": [
        {
          "tipo": "SUBDECLARACION_EXOGENA",
          "severidad": "ALTA",
          "explicacion_ia": "El contribuyente declaró $50M en ICA...",
          "detalle": {}
        }
      ],
      "explicacion_ia": "Contribuyente con alto riesgo de subdeclaración..."
    }
  ]
}
```

**Response (200) — Con include_partial=true (proceso en curso):**

```json
{
  "proceso_id": "uuid-del-proceso",
  "estado": "EN_PROCESO",
  "intento_id": 2,
  "parcial": true,
  "paginacion": {
    "page": 1,
    "page_size": 50,
    "total_registros": 995,
    "total_paginas": 20
  },
  "resultados": []
}
```

**Response (409) — Sin include_partial y proceso en curso:**

```json
{
  "error": "PROCESO_EN_PROCESO",
  "mensaje": "El proceso aún no ha terminado (estado: EN_PROCESO). Use include_partial=true para ver resultados parciales.",
  "estado": "EN_PROCESO",
  "progreso": {
    "porcentaje": 45.2,
    "procesados": 995,
    "faltantes": 1205
  }
}
```

---

## 4. GET /proceso/{id}/errors — Consultar errores

**Query parameters:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `intento_id` | int | null | Filtrar por intento (si null, muestra todos) |
| `capa` | string | null | Filtrar por capa: `MCP`, `ORACLE`, `LLM`, `POSTGRES`, `VALIDACION`, `PROCESO` |
| `nit` | string | null | Filtrar errores de detalle por NIT |

**Response (200):**

```json
{
  "proceso_id": "uuid-del-proceso",
  "errores_proceso": [
    {
      "id": 1,
      "intento_id": 1,
      "capa": "MCP",
      "codigo": "MCP_TIMEOUT",
      "mensaje": "Timeout al conectar con MCP Server después de 30s",
      "contexto": { "pagina": 15, "timeout_ms": 30000 },
      "created_at": "2026-06-20T10:05:00Z"
    }
  ],
  "errores_detalle": [
    {
      "contribuyente_nit": "9003189639",
      "capa": "LLM",
      "codigo": "LLM_TIMEOUT",
      "mensaje": "Timeout al analizar contribuyente con LLM (Tier 1: anthropic, Tier 2: nvidia_nim)",
      "contexto": { "tokens_entrada": 2500, "timeout_ms": 60000, "provider_intentado": "anthropic" },
      "created_at": "2026-06-20T10:10:00Z"
    }
  ],
  "total_errores_proceso": 1,
  "total_errores_detalle": 5
}
```

---

## 5. POST /analizar/{contribuyente_nit} — Análisis individual

**Endpoint:** `POST /api/v1/analizar/{contribuyente_nit}?periodo=2024`

| Parámetro | Tipo | Default | Requerido | Descripción |
|---|---|---|---|---|
| `contribuyente_nit` | string | — | Sí (path) | NIT del contribuyente a analizar |
| `periodo` | string | `2024` | No (query) | Año fiscal a analizar |

**Sin body** — el NIT va como path param y el período como query param.

**Response (200):**

```json
{
  "contribuyente_nit": "9012345678",
  "razon_social": "COMERCIO XYZ S.A.S.",
  "ciiu": "4711",
  "clasificacion": "INEXACTO",
  "mcp_score": 85.5,
  "mcp_razon": "",
  "srf_total": 78,
  "componentes_srf": [
    { "nombre": "consistencia", "valor": 80, "peso": 0.3 },
    { "nombre": "historial", "valor": 75, "peso": 0.4 },
    { "nombre": "declaracion", "valor": 82, "peso": 0.3 }
  ],
  "nivel_riesgo": "ALTO",
  "hallazgos": [
    {
      "tipo": "SUBDECLARACION_EXOGENA",
      "declarado_ica": 50000000,
      "exogena": 120000000,
      "diferencia": 70000000,
      "variacion_pct": 140,
      "explicacion_ia": "El contribuyente declaró $50M en ICA..."
    }
  ],
  "explicacion_ia": "Contribuyente con alto riesgo de subdeclaración...",
  "tokens_utilizados": 2500,
  "duracion_ms": 45000,
  "provider_utilizado": "anthropic",
  "cache_hit": false
}
```

**Response (404):**

```json
{
  "error": "NIT_NO_ENCONTRADO",
  "mensaje": "El NIT 9012345678 no fue encontrado en el padrón de contribuyentes"
}
```

**Response (429):**

```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "mensaje": "Límite de requests excedido. Intente en 60 segundos."
}
```

**Comportamiento:**

| Aspecto | Detalle |
|---|---|
| Timeout | 90 segundos max (RNF-01) |
| Fallback LLM | Se aplica la misma cadena de 3 tiers |
| No usa background | Ejecución sincrónica — espera resultado |
| No crea proceso | No inserta en `procesos` — es análisis on-demand |
| Cache | Si el mismo NIT + periodo fue analizado en < 1h, retorna cache |
| Errores | Si el NIT no tiene datos MCP, retorna 404 con explicación |

---

## 6. GET /contribuyente/{nit}/comportamiento — Análisis comportamental

**Endpoint:** `GET /api/v1/contribuyente/{contribuyente_nit}/comportamiento?periodo=2024&ciiu=&regimen=&min_pares=10`

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `contribuyente_nit` | string | — | NIT del contribuyente (path) |
| `periodo` | string | `2024` | Año fiscal (query) |
| `ciiu` | string | null | Código CIIU para filtrar grupo par |
| `regimen` | string | null | Régimen para filtrar grupo par |
| `min_pares` | int | 10 | Mínimo de pares para calcular benchmark (3-100) |

**Response (200):** Compara al contribuyente contra su grupo par (mismo CIIU + régimen).

```json
{
  "contribuyente_nit": "9012345678",
  "periodo": "2024",
  "score_comportamental": 72.4,
  "prioridad": "ALTA",
  "confianza": 0.85,
  "metricas": {
    "declaracion_oportuna": true,
    "variacion_ingresos_pct": -12.5,
    "retenciones_pct": 3.2,
    "antiguedad_dias": 45
  },
  "benchmark": {
    "tamano_grupo": 150,
    "media_score": 65.0,
    "desviacion_std": 15.3,
    "percentil_contribuyente": 75
  },
  "desviaciones": [
    {
      "metrica": "variacion_ingresos_pct",
      "valor_contribuyente": -12.5,
      "media_grupo": 2.1,
      "desviacion_std": 5.0,
      "z_score": -2.92,
      "significativa": true
    }
  ],
  "hallazgos": [
    "La variación de ingresos del contribuyente está 2.92 desviaciones por debajo de la media del grupo par"
  ],
  "explicacion": "El contribuyente presenta un score comportamental de 72.4, ubicándose en el percentil 75 de su grupo par..."
}
```

---

## 7. GET /proceso/{id}/ranking-comportamental — Ranking comportamental del proceso

**Endpoint:** `GET /api/v1/proceso/{proceso_id}/ranking-comportamental?periodo=&limite=50&min_score=0&min_pares=10`

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `proceso_id` | UUID | — | ID del proceso (path) |
| `periodo` | string | null | Año fiscal (query, opcional) |
| `limite` | int | 50 | Máximo de resultados (1-100) |
| `min_score` | float | 0 | Score mínimo para incluir (0-100) |
| `min_pares` | int | 10 | Mínimo de pares para incluir (3-100) |

**Response (200):**

```json
{
  "proceso_id": "uuid-del-proceso",
  "periodo": "2024",
  "total": 45,
  "ranking": [
    {
      "contribuyente_nit": "9012345678",
      "razon_social": "COMERCIO XYZ S.A.S.",
      "score_comportamental": 85.3,
      "prioridad": "ALTA",
      "confianza": 0.92,
      "num_pares": 120,
      "desviaciones_significativas": 3
    }
  ]
}
```

---

## 8. GET /contribuyente/{nit}/grafo-riesgo — Grafo de riesgo (conexiones empresariales)

**Endpoint:** `GET /api/v1/contribuyente/{contribuyente_nit}/grafo-riesgo?periodo=2024&min_pares=10&incluir_comportamiento=true`

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `contribuyente_nit` | string | — | NIT del contribuyente (path) |
| `periodo` | string | `2024` | Año fiscal (query) |
| `min_pares` | int | 10 | Mínimo de pares (3-100) |
| `incluir_comportamiento` | bool | `true` | Incluir análisis comportamental |

**Response (200):** Analiza conexiones empresariales (dirección, teléfono, correo, representante legal).

```json
{
  "nit_central": "9012345678",
  "periodo": "2024",
  "nodes": [
    { "id": "9012345678", "label": "COMERCIO XYZ S.A.S.", "tipo": "central", "score": 72.4 },
    { "id": "9012345679", "label": "INVERSIONES ABC LTDA", "tipo": "relacionado", "score": 45.0 },
    { "id": "9003189639", "label": "MUNICIPIO VALLEDUPAR", "tipo": "entidad", "score": null }
  ],
  "edges": [
    { "source": "9012345678", "target": "9012345679", "relacion": "COMPARTE_DIRECCION", "peso": 0.9 },
    { "source": "9012345678", "target": "9003189639", "relacion": "FISCALIZA", "peso": 1.0 }
  ],
  "resumen_red": {
    "total_nodos": 3,
    "total_conexiones": 2,
    "densidad_red": 0.33,
    "componentes_conexos": 1
  },
  "analisis_comportamental": {
    "score_comportamental": 72.4,
    "prioridad": "ALTA",
    "confianza": 0.85
  }
}
```

---

## 9. GET /contribuyente/{nit}/expediente-fiscal — Expediente fiscal unificado

**Endpoint:** `GET /api/v1/contribuyente/{contribuyente_nit}/expediente-fiscal?periodo=2024&min_pares=10`

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `contribuyente_nit` | string | — | NIT del contribuyente (path) |
| `periodo` | string | `2024` | Año fiscal (query) |
| `min_pares` | int | 10 | Mínimo de pares (3-100) |

**Response (200):**

```json
{
  "contribuyente_nit": "9012345678",
  "razon_social": "COMERCIO XYZ S.A.S.",
  "periodo": "2024",
  "score_fiscal_unificado": 78.5,
  "resumen_ejecutivo": "Contribuyente con riesgo ALTO. Presenta inconsistencias en ingresos reportados vs exógena...",
  "acciones_sugeridas": [
    "Requerir declaración corregida del período 2024",
    "Iniciar proceso de fiscalización electrónica",
    "Verificar retenciones practicadas"
  ],
  "markdown": "# Expediente Fiscal: COMERCIO XYZ S.A.S.\n\n## Resumen\n..."
}
```

---

## 10. POST /fiscalizacion/reglas/evaluar — Evaluar reglas fiscales

**Endpoint:** `POST /api/v1/fiscalizacion/reglas/evaluar`

**Body:** `PerfilFiscalRequest` (declaraciones, retenciones, exógena, facturación, contratos).

```json
{
  "contribuyente_nit": "9012345678",
  "periodo": "2024",
  "declaraciones": { "total_ingresos": 50000000, "impuesto_declarado": 1500000 },
  "retenciones": { "practicadas": 500000, "declaradas": 300000 },
  "exogena": { "ingresos_reportados": 120000000 },
  "facturacion": { "total_facturado": 130000000 },
  "contratos": { "total_contratos": 80000000 },
  "reglas": ["REGLA_001", "REGLA_002"]
}
```

**Response (200):**

```json
{
  "total": 2,
  "resultados": [
    {
      "codigo": "REGLA_001",
      "nombre": "Subdeclaración vs Exógena",
      "cumple": false,
      "severidad": "ALTA",
      "detalle": "Diferencia del 140% entre ingresos declarados y exógena",
      "valor_detectado": 70000000,
      "umbral": 5000000
    }
  ]
}
```

---

## 11. POST /fiscalizacion/reglas/evaluar/{nit} — Evaluar reglas por NIT (desde Oracle)

**Endpoint:** `POST /api/v1/fiscalizacion/reglas/evaluar/{contribuyente_nit}?periodo=2024&reglas=REGLA_001&reglas=REGLA_002`

Obtiene datos desde Oracle y evalúa reglas.

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `contribuyente_nit` | string | — | NIT del contribuyente (path) |
| `periodo` | string | `2024` | Año fiscal (query) |
| `reglas` | string[] | null | Lista opcional de reglas a evaluar |

**Response (200):** Mismo formato que §10.

---

## 12. POST /fiscalizacion/reglas/ejecutar — Ejecutar reglas (persiste hallazgos)

**Endpoint:** `POST /api/v1/fiscalizacion/reglas/ejecutar`

Similar a evaluar (`PerfilFiscalRequest`) pero persiste los hallazgos en BD. Acepta `proceso_id` y `entidad_id` opcionales.

**Response (201):**

```json
[
  {
    "id": "uuid-del-hallazgo",
    "contribuyente_nit": "9012345678",
    "regla": "REGLA_001",
    "tipo": "INCONSISTENCIA",
    "severidad": "ALTA",
    "descripcion": "Subdeclaración detectada vs exógena",
    "estado": "PENDIENTE",
    "accionable": true,
    "created_at": "2026-06-21T10:30:00Z"
  }
]
```

También existe `POST /fiscalizacion/reglas/ejecutar/{contribuyente_nit}` que obtiene datos desde Oracle y ejecuta.

---

## 13. POST /fiscalizacion/hallazgos — Crear hallazgo manual

**Endpoint:** `POST /api/v1/fiscalizacion/hallazgos`

```json
{
  "contribuyente_nit": "9012345678",
  "regla": "REGLA_MANUAL",
  "tipo": "OBSERVACION",
  "severidad": "MEDIA",
  "descripcion": "Hallazgo creado manualmente por funcionario",
  "proceso_id": null,
  "entidad_id": null
}
```

**Response (201):** Hallazgo creado con `id`, `estado: "PENDIENTE"`, `created_at`.

---

## 14. GET /fiscalizacion/hallazgos — Listar hallazgos

**Endpoint:** `GET /api/v1/fiscalizacion/hallazgos?estado=&regla=&contribuyente_nit=&accionable=&page=1&page_size=50`

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `estado` | string | null | Filtrar por estado |
| `regla` | string | null | Filtrar por código de regla |
| `contribuyente_nit` | string | null | Filtrar por NIT |
| `accionable` | bool | null | Filtrar solo accionables |
| `page` | int | 1 | Número de página |
| `page_size` | int | 50 | Registros por página (max 200) |

**Response (200):**

```json
{
  "total": 150,
  "page": 1,
  "page_size": 50,
  "resultados": [
    {
      "id": "uuid",
      "contribuyente_nit": "9012345678",
      "regla": "REGLA_001",
      "tipo": "INCONSISTENCIA",
      "severidad": "ALTA",
      "descripcion": "...",
      "estado": "PENDIENTE",
      "accionable": true,
      "created_at": "2026-06-21T10:30:00Z"
    }
  ]
}
```

---

## 15. GET /fiscalizacion/hallazgos/{id} — Detalle de hallazgo

**Endpoint:** `GET /api/v1/fiscalizacion/hallazgos/{hallazgo_id}`

**Response (200):** Mismo formato individual que el `HallazgoResponse` de §12.

---

## 16. POST /fiscalizacion/hallazgos/{id}/revision — Revisión humana

**Endpoint:** `POST /api/v1/fiscalizacion/hallazgos/{hallazgo_id}/revision`

```json
{
  "funcionario_id": "uuid-del-funcionario",
  "decision": "ACEPTADO",
  "motivo": "Hallazgo válido, se procede con requerimiento"
}
```

`decision` puede ser: `ACEPTADO`, `RECHAZADO`, `EN_REVISION`.

**Response (200):** Hallazgo actualizado con `estado`, `revisado_por`, `revisado_en`.

---

## 17. POST /fiscalizacion/hallazgos/{id}/revision-agente — Revisión asistida por IA

**Endpoint:** `POST /api/v1/fiscalizacion/hallazgos/{hallazgo_id}/revision-agente`

```json
{
  "usar_ia": true
}
```

**Response (200):** Incluye análisis del agente IA y recomendación.

```json
{
  "hallazgo_id": "uuid",
  "analisis_agente": "El hallazgo es consistente con los datos fiscales...",
  "recomendacion": "ACEPTADO",
  "confianza": 0.88,
  "revisado_en": "2026-06-21T11:00:00Z"
}
```

---

## 18. POST /entidad_fiscalizadora — Crear entidad fiscalizadora

**Endpoint:** `POST /api/v1/entidad_fiscalizadora`

```json
{
  "entidad_nit": "9003189639",
  "nombre": "Municipio de Valledupar",
  "email": "fiscalia@valledupar.gov.co"
}
```

**Response (201):**

```json
{
  "id": "uuid",
  "entidad_nit": "9003189639",
  "nombre": "Municipio de Valledupar",
  "email": "fiscalia@valledupar.gov.co",
  "activo": true
}
```

---

## 19. GET /entidad_fiscalizadora/{nit} — Obtener entidad por NIT

**Endpoint:** `GET /api/v1/entidad_fiscalizadora/{entidad_nit}`

**Response (200):** Mismo formato que `EntidadResponse`.

**Response (404):** `EntidadNoEncontradoError`.

---

## 20. GET /entidades_fiscalizadoras — Listar entidades

**Endpoint:** `GET /api/v1/entidades_fiscalizadoras?page=1&page_size=20`

**Response (200):**

```json
{
  "page": 1,
  "page_size": 20,
  "mensaje": "Listado no implementado"
}
```

---

## 21. GET /proceso/{id}/export — Exportar resultados a Excel

**Endpoint:** `GET /api/v1/proceso/{proceso_id}/export?formato=xlsx`

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `proceso_id` | UUID | — | ID del proceso (path) |
| `formato` | string | `xlsx` | Formato de exportación (solo xlsx) |

**Response (200):** `StreamingResponse` con `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` y archivo `.xlsx` con dos hojas:
- **Resumen**: datos agregados del proceso
- **Resultados Campaña**: detalle por NIT con columnas NIT, Razón Social, CIIU, Clasificación, Score Unificado, SRF, Nivel Riesgo, Hallazgos, Explicación IA

---

## 22. GET /visor/grafo/{nit} — Visor HTML interactivo del grafo de riesgo

**Endpoint:** `GET /api/v1/visor/grafo/{contribuyente_nit}?periodo=2024`

Retorna una página HTML interactiva con el grafo de riesgo del contribuyente (rendereado con librería gráfica en el frontend).

---

## 23. Seguridad y Operaciones

> **Modelo de seguridad:** Solo red privada OCI. Sin autenticación por API key — APEX es el único consumidor y accede vía red interna.

### Rate Limiting

| Endpoint | Límite | Ventana |
|---|---|---|
| `POST /proceso` | 10 requests | por minuto por IP |
| `GET /proceso/{id}/status` | 60 requests | por minuto por IP |
| `GET /proceso/{id}/results` | 30 requests | por minuto por IP |
| `GET /proceso/{id}/errors` | 30 requests | por minuto por IP |
| `POST /analizar/{nit}` | 5 requests | por minuto por IP |
| `GET /health` | Sin límite | — |

**Implementación:** In-memory rate limiter (V1). Futuro: Redis.

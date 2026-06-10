# API Endpoints — FiscalIA Microservicio

## Base URL

```
http://<host>:8000/api/v1
```

## Autenticación

Todas las solicitudes (excepto `/health`) requieren el header:

```
X-API-Key: <api_key_configurada_en_.env>
```

Si no se envía, retorna `401 Unauthorized`.

---

## 1. Health Check

### `GET /api/v1/health`

Verifica el estado del microservicio y conectividad con Oracle.

**Response 200:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "llm_provider": "nvidia_nim/meta/llama-3.3-70b-instruct",
  "llm_fallback": "nvidia_nim/meta/llama-3.2-3b-instruct",
  "oracle_connected": true,
  "uptime_seconds": 86400,
  "cache_size": 42,
  "cache_ttl": 3600
}
```

| Campo | Descripción |
|---|---|
| `status` | `healthy` si Oracle conecta, `degraded` si no |
| `llm_provider` | Proveedor y modelo LLM primario configurado |
| `llm_fallback` | Proveedor y modelo de respaldo |
| `oracle_connected` | `true` si la conexión a Oracle es exitosa |
| `uptime_seconds` | Segundos desde el inicio del microservicio |
| `cache_size` | Número de respuestas en caché |
| `cache_ttl` | TTL configurado de la caché en segundos |

---

## 2. Análisis Completo

### `POST /api/v1/analizar/{nit}`

Ejecuta el pipeline completo: cruce exógena, inconsistencias, SRF, y explicación con IA.

**Parámetros:**

| Parámetro | Tipo | Ubicación | Obligatorio | Descripción |
|---|---|---|---|---|
| `nit` | string | Path | Sí | NIT del contribuyente (sin guiones) |
| `periodo` | string | Query | Sí | Período en formato YYYY-MM |

**Request example:**
```
POST /api/v1/analizar/9003189639?periodo=2025-01
X-API-Key: abc123...
```

**Response 200:**
```json
{
  "nit": "9003189639",
  "periodo": "2025-01",
  "score_riesgo": 85,
  "nivel_riesgo": "ALTO",
  "hallazgos": [
    {
      "tipo": "SUBREGISTRO",
      "severidad": "ALTA",
      "descripcion": "Posible subdeclaración en CIIU 4711. Exógena reporta $120M vs ICA $50M",
      "diferencia": 70000000,
      "ciiu": "4711"
    },
    {
      "tipo": "TARIFA",
      "severidad": "MEDIA",
      "descripcion": "Tarifa ICA aplicada 0.004 vs tarifa vigente 0.006 para CIIU 4711",
      "diferencia": 2000000,
      "ciiu": "4711"
    }
  ],
  "explicacion_srf": "El Score de Riesgo Fiscal se ubica en nivel ALTO (85/100). El factor de mayor peso es la diferencia entre ingresos reportados en exógena y declarados en ICA ($70M), seguido de la discrepancia en la tarifa CIIU aplicada.",
  "tiempo_analisis_ms": 45200,
  "cache_hit": false,
  "modo_degradado": false
}
```

**Response 401** (sin API Key):
```json
{
  "detail": "API Key inválida"
}
```

**Response 500** (error interno):
```json
{
  "message": "Error interno del servidor",
  "detail": "Error conectando a Oracle DB"
}
```

| Campo | Descripción |
|---|---|
| `score_riesgo` | SRF de 0 a 100 |
| `nivel_riesgo` | `BAJO` (<40), `MEDIO` (40-70), `ALTO` (>70) |
| `hallazgos[]` | Lista de inconsistencias detectadas |
| `explicacion_srf` | Explicación en lenguaje natural generada por IA |
| `tiempo_analisis_ms` | Tiempo total del análisis en milisegundos |
| `cache_hit` | `true` si el resultado fue servido desde caché |
| `modo_degradado` | `true` si el LLM no estuvo disponible |

---

## 3. Score de Riesgo Fiscal

### `POST /api/v1/score/{nit}`

Calcula únicamente el SRF y genera la explicación con IA (sin análisis completo de inconsistencias).

**Parámetros:**

| Parámetro | Tipo | Ubicación | Obligatorio |
|---|---|---|---|
| `nit` | string | Path | Sí |
| `periodo` | string | Query | Sí |

**Request example:**
```
POST /api/v1/score/9003189639?periodo=2025-01
X-API-Key: abc123...
```

**Response 200:**
```json
{
  "nit": "9003189639",
  "srf": 72,
  "nivel": "ALTO",
  "componentes": [
    { "nombre": "Diferencia exógena vs ICA", "valor": 30, "peso": 35 },
    { "nombre": "Antigüedad sin declarar", "valor": 15, "peso": 20 },
    { "nombre": "Discrepancia tarifa CIIU", "valor": 22, "peso": 25 },
    { "nombre": "Estado RUES vs padrón", "valor": 5, "peso": 20 }
  ],
  "explicacion_ia": "Los principales factores de riesgo son: (1) la diferencia entre ingresos reportados en exógena vs declarados en ICA, (2) la tarifa CIIU aplicada no corresponde a la vigente, y (3) el contribuyente presenta 2 períodos sin declarar.",
  "tiempo_analisis_ms": 12300
}
```

---

## 4. Root

### `GET /`

Información básica del microservicio.

**Response 200:**
```json
{
  "message": "FiscalIA - Microservicio OCI",
  "version": "2.0.0",
  "status": "running"
}
```

---

## 5. Documentación Interactiva

| URL | Descripción |
|---|---|
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/openapi.json` | Especificación OpenAPI en JSON |

---

## 6. Códigos de Estado HTTP

| Código | Significado |
|---|---|
| 200 | Solicitud exitosa |
| 401 | API Key inválida o faltante |
| 422 | Error de validación (parámetros incorrectos) |
| 500 | Error interno del servidor |
| 503 | Servicio degradado (Oracle o LLM no disponibles) |

# Configuración del LLM — FiscalIA Microservicio

## 1. Arquitectura LLM

```
litellm.Router
    │
    ├── primary:   NVIDIA NIM (gratis, default)
    │   └── meta/llama-3.3-70b-instruct
    │
    └── fallback:  NVIDIA NIM (misma key, modelo ligero)
        └── meta/llama-3.2-3b-instruct
```

El microservicio usa **litellm Router** con soporte de **fallback automático**. Si el proveedor primario falla (timeout, error HTTP, rate limit), litellm redirige automáticamente al fallback sin cambiar una línea de código.

> **Cambio de HuggingFace a NVIDIA NIM**: El fallback original (Hugging Face Mistral 7B) se reemplazó porque el token gratuito de HF no tiene permisos para Inference Providers. Gemini presentaba rate limiting excesivo. NVIDIA llama-3.2-3b usa la misma API key, es más rápido y funciona consistentemente.

---

## 2. Proveedores Soportados

| Proveedor | `LLM_PRIMARY_PROVIDER` | `LLM_PRIMARY_MODEL` | API Key |
|---|---|---|---|
| **NVIDIA NIM** (default) | `nvidia_nim` | `meta/llama-3.3-70b-instruct` | NVIDIA API |
| **NVIDIA NIM** (fallback) | `nvidia_nim` | `meta/llama-3.2-3b-instruct` | NVIDIA API |
| OpenAI | `openai` | `gpt-4o`, `gpt-4o-mini` | OpenAI API Key |
| Anthropic | `anthropic` | `claude-sonnet-4`, `claude-haiku` | Anthropic API Key |
| Azure OpenAI | `azure` | `gpt-4o` | Azure API Key + base |
| Ollama (local) | `ollama` | `llama3`, `mistral` | No requiere |
| Google Gemini | `gemini` | `gemini-2.0-flash` | Google API Key |
| AWS Bedrock | `bedrock` | `anthropic.claude-sonnet` | AWS Credentials |

---

## 3. Cambio de Proveedor

Para cambiar el proveedor principal, solo se edita `.env`:

**Ejemplo: Cambiar a OpenAI GPT-4o como primary:**
```env
LLM_PRIMARY_PROVIDER=openai
LLM_PRIMARY_MODEL=gpt-4o
LLM_PRIMARY_API_KEY=sk-proj-...
LLM_PRIMARY_API_BASE=
```

**Ejemplo: Solo NVIDIA (sin fallback):**
```env
LLM_MODE=primary_only
LLM_PRIMARY_PROVIDER=nvidia_nim
LLM_PRIMARY_MODEL=meta/llama-3.3-70b-instruct
LLM_PRIMARY_API_KEY=nvapi-...
```

**Ejemplo: Ollama local (sin fallback):**
```env
LLM_MODE=primary_only
LLM_PRIMARY_PROVIDER=ollama
LLM_PRIMARY_MODEL=llama3
LLM_PRIMARY_API_KEY=
```

---

## 4. Fallback Automático

Cuando `LLM_MODE=primary_fallback`, el comportamiento es:

```
1. Intentar primary (ej: NVIDIA NIM)
2. Si primary falla → intentar fallback (ej: NVIDIA NIM 3B)
3. Si fallback también falla → retornar respuesta degradada
   (análisis sin lenguaje natural, solo datos de cruces)
```

La respuesta degradada se ve así:
```json
{
  "explicacion": "El análisis con IA no está disponible en este momento. Los cruces e inconsistencias se presentan sin generación de lenguaje natural.",
  "modo_degradado": true
}
```

---

## 5. Estructura de Prompts

### 5.1. Prompt de Análisis Completo

```text
Eres un asistente de fiscalización del Impuesto de Industria y Comercio (ICA)
en Valledupar, Colombia.

NIT: {nit}
Período: {periodo}

CRUCES EXÓGENA VS DECLARADO:
{json de cruces}

INCONSISTENCIAS:
{json de inconsistencias}

SRF: {json del score}

Genera un JSON con:
1. "explicacion": explicación del SRF y factores de riesgo
2. "hallazgos_enriquecidos": array con explicación y recomendación
```

### 5.2. Prompt de Explicación SRF

```text
Eres un asistente de fiscalización del ICA en Valledupar, Colombia.

NIT: {nit}
Período: {periodo}
SRF: {json del score}

Genera un JSON con:
1. "explicacion": explica el SRF en lenguaje natural para el funcionario
```

---

## 6. Configuración del LLM

| Parámetro | Valor | Razón |
|---|---|---|
| `temperature` | `0.1` | Bajo para evitar creatividad, queremos respuestas consistentes |
| `max_tokens` | `4096` | Suficiente para el análisis de un contribuyente |
| `timeout` | `60s` | Balance entre esperar respuesta y no bloquear |
| `retry_attempts` | `3` | Suficiente para superar errores transitorios |
| `retry_backoff` | `2x` | Backoff exponencial: 2s, 4s, 8s |

---

## 7. Consumo de Tokens

Cada análisis queda registrado en `FISCAL_ANALISIS_IA` con:

- `tokens_entrada`: tokens del prompt enviado
- `tokens_salida`: tokens de la respuesta generada
- `costo_estimado`: costo estimado en USD

Esto permite monitorear el consumo y optimizar los prompts si es necesario.

# Despliegue en OCI Container Instance

## 1. Requisitos

- Oracle Cloud Infrastructure (OCI) tenant activo
- Acceso a OCI Container Registry (OCIR)
- PostgreSQL 16+ accesible desde la VCN
- API Keys: Anthropic/OpenAI (Tier 1), NVIDIA NIM (Tier 2), HuggingFace (Tier 3)

---

## 2. Build de la Imagen Docker

```bash
# Construir imagen
docker build -t iat/fiscalia-ia:latest .

# Taggear para OCI Registry
docker tag iat/fiscalia-ia:latest <region>.ocir.io/<namespace>/fiscalia-ia:latest

# Autenticarse en OCI Registry
docker login <region>.ocir.io

# Push
docker push <region>.ocir.io/<namespace>/fiscalia-ia:latest
```

---

## 3. Creación de OCI Container Instance

### 3.1. Configuración de Red

- **VCN:** Usar la VCN existente del proyecto Taxation Smart de Valledupar
- **Subred:** Privada (sin IP pública)
- **NSG:** Regla de entrada solo desde el rango de IPs de APEX
- **Puerto:** 8000

### 3.2. Variables de Entorno

Configurar desde **OCI Vault** (no en texto plano):

```
# PostgreSQL
POSTGRES_HOST=10.0.1.100
POSTGRES_PORT=5432
POSTGRES_DB=fiscalia
POSTGRES_USER=fiscalia
POSTGRES_PASSWORD=

# LLM Tier 1 (pago)
LLM_TIER1_PROVIDER=anthropic
LLM_TIER1_API_KEY=
LLM_TIER1_MODEL=claude-sonnet-4-20250506

# LLM Tier 2 (NVIDIA NIM)
LLM_TIER2_API_KEY=
LLM_TIER2_MODEL=qwen/qwen2.5-7b-instruct

# LLM Tier 3 (HuggingFace)
LLM_TIER3_API_KEY=
LLM_TIER3_MODEL=Qwen/Qwen2.5-7B-Instruct
```

### 3.3. Health Check

```
Ruta:  /api/v1/health
Puerto: 8000
Intervalo: 30s
Timeout: 10s
Umbral: 3 intentos fallidos
```

### 3.4. Recursos

| Recurso | Valor |
|---|---|
| CPU | 1 OCPU |
| Memoria | 8 GB |
| Disco | 10 GB |
| Instancias | 1 (V1, sin escalamiento horizontal) |

---

## 4. Integración con Oracle APEX

APEX consume el microservicio mediante **Dynamic Actions**:

### 4.1. Crear REST Data Source

1. Navegar a **Workspace Utilities → REST Data Sources**
2. Crear nuevo REST Data Source
3. URL: `http://<container-ip>:8000/api/v1`
4. Probar conexión con `GET /health`

### 4.2. Llamar al Análisis

```sql
-- Desde PL/SQL APEX
DECLARE
    l_response clob;
BEGIN
    l_response := apex_web_service.make_rest_request(
        p_url         => 'http://<container-ip>:8000/api/v1/analizar/9003189639',
        p_http_method => 'POST',
        p_body        => '{ "entidad_nit": "9003189639", "nit_objetivo": "9012345678" }'
    );
END;
```

---

## 5. Monitoreo

### 5.1. Logs

- OCI Logging recibe stdout del contenedor
- Cada análisis genera un log estructurado con: `nit`, `periodo`, `tiempo_ms`, `tokens`, `cache_hit`, `provider`

### 5.2. Métricas

- Latencia por endpoint (target < 90s)
- Tokens consumidos por período
- Cache hit ratio
- Errores 5xx
- Estado de conexión PostgreSQL

### 5.3. Alarmas sugeridas

| Alarma | Umbral | Acción |
|---|---|---|
| Latencia > 90s | > 3 ocurrencias en 5 min | Notificar al equipo |
| Errores 5xx | > 5 en 5 min | Notificar al equipo |
| Conexión PostgreSQL caída | 1 ocurrencia | Notificar al equipo |
| Costo LLM mensual | > $100 USD | Revisar uso y optimizar prompts |

---

## 6. Actualización

```bash
# Build nueva versión
docker build -t iat/fiscalia-ia:2.0.1 .

# Push
docker push <region>.ocir.io/<namespace>/fiscalia-ia:2.0.1

# Actualizar Container Instance
oci container-instances container-instance update \
    --container-instance-id <id> \
    --image <region>.ocir.io/<namespace>/fiscalia-ia:2.0.1
```

La actualización es **rolling** sin downtime si se configura más de 1 instancia (V2+).

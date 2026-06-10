# Despliegue en OCI Container Instance

## 1. Requisitos

- Oracle Cloud Infrastructure (OCI) tenant activo
- Acceso a OCI Container Registry (OCIR)
- Oracle Database 19c+ accesible desde la VCN
- API Key de NVIDIA NIM

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
API_KEY=...
ORACLE_DSN=...
ORACLE_USER=...
ORACLE_PASSWORD=...
LLM_PRIMARY_API_KEY=...
LLM_FALLBACK_API_KEY=...
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
4. Autenticación: API Key en header `X-API-Key`
5. Probar conexión con `GET /health`

### 4.2. Llamar al Análisis

```sql
-- Desde PL/SQL APEX
DECLARE
    l_response clob;
BEGIN
    l_response := apex_web_service.make_rest_request(
        p_url         => 'http://<container-ip>:8000/api/v1/analizar/9003189639?periodo=2025-01',
        p_http_method => 'POST',
        p_username    => null,
        p_password    => null,
        p_api_key     => 'X-API-Key',
        p_api_value   => 'abc123...'
    );
END;
```

---

## 5. Monitoreo

### 5.1. Logs

- OCI Logging recibe stdout del contenedor
- Cada análisis genera un log estructurado con: `nit`, `periodo`, `tiempo_ms`, `tokens`, `cache_hit`, `modo_degradado`

### 5.2. Métricas

- Latencia por endpoint (target < 90s)
- Tokens consumidos por período
- Cache hit ratio
- Errores 5xx
- Estado de conexión Oracle

### 5.3. Alarmas sugeridas

| Alarma | Umbral | Acción |
|---|---|---|
| Latencia > 90s | > 3 ocurrencias en 5 min | Notificar al equipo |
| Errores 5xx | > 5 en 5 min | Notificar al equipo |
| Conexión Oracle caída | 1 ocurrencia | Notificar al equipo |
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

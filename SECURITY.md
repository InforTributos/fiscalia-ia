# Política de Seguridad — FiscalIA

## Versiones Soportadas

| Versión | Soportada |
|---|---|
| 2.x | ✅ |
| 1.x | ❌ (fin de vida) |

## Reporte de Vulnerabilidades

Si encuentras una vulnerabilidad de seguridad:

1. **No abras un issue público.** Envía un correo al equipo de seguridad.
2. Incluye:
   - Descripción de la vulnerabilidad
   - Pasos para reproducir
   - Impacto potencial
   - (Opcional) Propuesta de mitigación

### Contacto

- **Email:** seguridad@informaticaytributos.com
- **SLAs:**
  - Acuse de recibo: 48h hábiles
  - Evaluación inicial: 5 días hábiles
  - Parche crítico: 15 días hábiles
  - Parche estándar: 30 días hábiles

## Datos Sensibles

- Las API keys de LLM se configuran exclusivamente vía `.env` o **OCI Vault** (no hardcodeadas).
- El archivo `.env` **no se commitea** al repositorio.
- Las conexiones a PostgreSQL deben usar contraseñas seguras rotadas periódicamente.
- Los logs **no deben contener** tokens, API keys, contraseñas ni datos personales del contribuyente.

## Buenas Prácticas

- Mantener dependencias actualizadas (`pip-audit` periódico).
- No exponer stack traces internos en respuestas HTTP (manejado por `error_handler.py`).
- Rate limiting activo en todos los endpoints de análisis.
- Validación estricta de entrada vía Pydantic schemas.
- Caché en memoria con TTL para evitar re-procesamiento de NITs repetidos.

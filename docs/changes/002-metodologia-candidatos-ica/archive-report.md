# Archive Report: Alinear FiscalIA con metodologia real de candidatos ICA

## Summary

Se implementaron 4 nuevas funciones en `pagination.py` y 1 en `classify.py` alineando el codigo con el esquema real de tablas Oracle documentado en la metodologia de candidatos ICA v1.0 (Valledupar). Cobertura alcanzo el quality gate de 80%.

## Decisions Made

- **Queries SQL como constantes de modulo**: Las 4 queries complejas se definen como constantes `*_SQL` en `pagination.py` para facilitar revision y mantenimiento. Alternativa descartada: construir queries dinamicamente con string formatting (mas fragil).
- **Exclusion via NOT EXISTS**: El filtro anti-duplicados FI_* se implementa como subconsultas SQL en Oracle, no en Python. Esto mantiene la responsabilidad de filtrado en la capa de datos.
- **Umbral de retenciones default 5%**: Configurable via parametro `umbral_pct`. La tolerancia evita falsos positivos por redondeos.
- **`clasificar_candidato()` como complemento, no reemplazo**: La funcion legacy `clasificar_nit()` se mantiene para backward compatibility con routers que aun no usan los nuevos tipos.

## Lessons Learned

1. **Async generators**: Las funciones nuevas son async generators (`yield` dentro de `async def`). Los tests deben iterarlas con `async for`.
2. **`_Call.__getitem__`**: Ya documentado en ciclo 001 — `call[1]` son kwargs, no args posicionales.
3. **Nombres de columnas Oracle**: El documento de metodologia usa nombres abreviados (ej: `idntfccion`, `nmbre_rzon_scial`). Las queries SQL heredan estos nombres exactos.
4. **JOINs entre SI_* y GI_* via `id_sjto_impsto`**: El campo `id_sjto_impsto` es la llave que une inscripcion ICA, persona, sujeto y declaraciones.

## Follow-ups

- Adaptar `crosscheck_service.py` (SRF) para los 4 nuevos tipos de candidatos
- Adaptar `orquestar_proceso.py` para invocar las nuevas funciones de deteccion
- Parametrizar periodo (sigue hardcodeado)
- Ingesta del archivo DIAN a `TEMP_RQ_DIAN` (responsabilidad APEX)
- Tests adicionales de edge cases (exclusion, tarifas iguales, exogena vacia)

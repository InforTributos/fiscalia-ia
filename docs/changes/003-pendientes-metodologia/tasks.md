# Tasks: Adaptar SRF y orquestador

**Strict TDD active.**

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| 1 | RED | Write test: `test_clasificar_omiso_conocido_en_datos` | tests/unit/test_crosscheck.py | — | Test verifica OMISO_CONOCIDO |
| 2 | GREEN | Update `clasificar_por_datos()` para nuevos tipos | crosscheck_service.py | 1 | Test pasa |
| 3 | RED | Write test: `test_inexacto_ciiu_genera_inconsistencia` | tests/unit/test_crosscheck.py | — | Test verifica inconsistencia CIIU |
| 4 | GREEN | Agregar deteccion CIIU en `extraer_inconsistencias()` | crosscheck_service.py | 3 | Test pasa |
| 5 | RED | Write test: `test_inexacto_retenciones_genera_inconsistencia` | tests/unit/test_crosscheck.py | — | Test verifica inconsistencia retenciones |
| 6 | GREEN | Agregar deteccion retenciones en `extraer_inconsistencias()` | crosscheck_service.py | 5 | Test pasa |
| 7 | GREEN | Parametrizar periodo en `orquestar_proceso.py` | orquestar_proceso.py | — | Hardcodeado eliminado |
| 8 | REFACTOR | Run full suite + lint | all | 7 | 153+ tests pass, lint clean |

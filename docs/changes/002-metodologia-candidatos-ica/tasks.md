# Tasks: Alinear FiscalIA con metodologia real de candidatos ICA

**Strict TDD active.** Every GREEN task requires a preceding RED task.

---

## Grupo A: Reescritura de `obtener_datos_fiscales()` con tablas reales (4 tasks)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| A1 | RED | Write test: `test_obtener_datos_fiscales_usa_tablas_reales` | `tests/unit/test_pagination.py` | — | Test verifica que las queries usan SI_C_SUJETOS, SI_I_PERSONAS, SI_I_SUJETOS_IMPUESTO, GI_G_DECLARACIONES |
| A2 | GREEN | Actualizar `OBTENER_CONTRIBUYENTE_SQL` y `OBTENER_DECLARACIONES_SQL` | `pagination.py` | A1 | Tests pasan con nuevas queries |
| A3 | RED | Write test: `test_obtener_datos_fiscales_incluye_exclusion` | `tests/unit/test_pagination.py` | — | Test verifica exclusion FI_* en datos fiscales |
| A4 | GREEN | Agregar subquery de exclusion FI_* a `obtener_datos_fiscales` | `pagination.py` | A3 | Tests pasan con filtro exclusion |

## Grupo B: Omisos Conocidos (5 tasks)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| B1 | RED | Write test: `test_omisos_conocidos_query_estructura` | `tests/unit/test_pagination.py` | — | Test verifica SQL incluye 4 tablas + filtros + NOT EXISTS declaraciones + NOT EXISTS FI_* |
| B2 | GREEN | Implementar `obtener_omisos_conocidos()` con query real | `pagination.py` | B1 | Test pasa |
| B3 | RED | Write test: `test_omisos_conocidos_excluye_con_declaracion` | `tests/unit/test_pagination.py` | — | Test: mock con declaracion → resultado vacio |
| B4 | RED | Write test: `test_omisos_conocidos_excluye_con_expediente` | `tests/unit/test_pagination.py` | — | Test: mock con expediente FI_* → resultado vacio |
| B5 | GREEN | Ejecutar B3+B4 → deben pasar con implementacion de B2 | `pagination.py` | B3, B4 | Tests pasan |

## Grupo C: Omisos Desconocidos (4 tasks)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| C1 | RED | Write test: `test_omisos_desconocidos_dian_sin_registro` | `tests/unit/test_pagination.py` | — | Test: NIT en DIAN, no en SI_C_SUJETOS → candidato |
| C2 | GREEN | Implementar `obtener_omisos_desconocidos()` — fuente DIAN | `pagination.py` | C1 | Test pasa |
| C3 | RED | Write test: `test_omisos_desconocidos_exogena_sin_registro` | `tests/unit/test_pagination.py` | — | Test: NIT en exogena, no en SI_C_SUJETOS → candidato |
| C4 | GREEN | Agregar fuente exogena a `obtener_omisos_desconocidos()` | `pagination.py` | C3 | Test pasa |

## Grupo D: Inexactos CIIU (3 tasks)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| D1 | RED | Write test: `test_inexactos_ciiu_tarifa_dian_mayor` | `tests/unit/test_pagination.py` | — | Test: CIIU diferente + tarifa DIAN > declarada → candidato |
| D2 | GREEN | Implementar `obtener_inexactos_ciiu()` | `pagination.py` | D1 | Test pasa |
| D3 | RED | Write test: `test_inexactos_ciiu_tarifa_dian_menor_no_alerta` | `tests/unit/test_pagination.py` | — | Test: tarifa DIAN <= declarada → no candidato |

## Grupo E: Inexactos Retenciones (3 tasks)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| E1 | RED | Write test: `test_inexactos_retenciones_diferencia_mayor_umbral` | `tests/unit/test_pagination.py` | — | Test: diferencia >5% → candidato |
| E2 | GREEN | Implementar `obtener_inexactos_retenciones()` | `pagination.py` | E1 | Test pasa |
| E3 | RED | Write test: `test_inexactos_retenciones_diferencia_menor_umbral` | `tests/unit/test_pagination.py` | — | Test: diferencia <5% → no candidato |

## Grupo F: Classify expandido (5 tasks)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| F1 | RED | Write test: `test_clasificar_omiso_conocido` | `tests/unit/test_classify.py` | — | Test: tipo=OMISO_CONOCIDO |
| F2 | RED | Write test: `test_clasificar_omiso_desconocido` | `tests/unit/test_classify.py` | — | Test: tipo=OMISO_DESCONOCIDO |
| F3 | RED | Write test: `test_clasificar_inexacto_ciiu` | `tests/unit/test_classify.py` | — | Test: tipo=INEXACTO_CIIU |
| F4 | RED | Write test: `test_clasificar_inexacto_retenciones` | `tests/unit/test_classify.py` | — | Test: tipo=INEXACTO_RETENCIONES |
| F5 | GREEN | Implementar `clasificar_candidato()` en classify.py | `classify.py` | F1-F4 | Tests pasan |

## Grupo G: REFACTOR y regresion (3 tasks)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| G1 | REFACTOR | Actualizar tests existentes de pagination con nuevas queries | `tests/unit/test_pagination.py` | A-E | 144 tests pasan |
| G2 | REFACTOR | Run lint + format | all changed files | G1 | ruff 0 errors |
| G3 | REFACTOR | Medir coverage delta | tests/unit/ | G2 | Mantener o subir de 79% |

---

**Total: 28 tasks (22 RED + 6 GREEN/REFACTOR).**

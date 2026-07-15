# Tasks: Tests de caracterizacion del modulo MCP

**Strict TDD activated for characterization tests.** RED phase: write test first, verify it describes expected behavior correctly, then GREEN phase: confirm it passes with existing code. For characterization tests, "failing" means the test correctly captures current behavior — it will pass immediately since code already exists.

Rationale: El codigo ya existe. Los tests de caracterizacion documentan el comportamiento actual. RED phase verifica que el test compila y describe correctamente el comportamiento. GREEN phase confirma que el codigo existente satisface el test.

---

## Grupo A: oracle_adapter.py (5 tasks)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| A1 | RED | Write test: `test_init_popula_settings` | `tests/unit/test_oracle_adapter.py` | — | Test loads settings correctly |
| A2 | RED | Write test: `test_get_token_hace_post_y_retorna_token` | `tests/unit/test_oracle_adapter.py` | — | Test verifies POST call and token extraction |
| A3 | RED | Write test: `test_call_tool_ensambla_request_y_parsea_json` | `tests/unit/test_oracle_adapter.py` | — | Test verifies full call_tool flow |
| A4 | RED | Write test: `test_call_tool_content_vacio_retorna_empty_dict` | `tests/unit/test_oracle_adapter.py` | — | Test verifies empty content handling |
| A5 | RED | Write test: `test_close_no_op` | `tests/unit/test_oracle_adapter.py` | — | Test verifies close() doesn't crash |

**GREEN phase for all A tests**: Run all tests → all pass immediately (code exists)

## Grupo B: pagination.py (7 tasks)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| B1 | RED | Write test: `test_obtener_datos_fiscales_retorna_dict_completo` | `tests/unit/test_pagination.py` | — | Test verifies assembled dict |
| B2 | RED | Write test: `test_obtener_datos_fiscales_sin_contribuyente_retorna_none` | `tests/unit/test_pagination.py` | — | Test verifies None return on empty |
| B3 | RED | Write test: `test_obtener_datos_fiscales_contribuyente_dict_sin_lista` | `tests/unit/test_pagination.py` | — | Test verifies single dict handling |
| B4 | RED | Write test: `test_obtener_datos_fiscales_sin_declaraciones` | `tests/unit/test_pagination.py` | — | Test verifies listas vacias seguras |
| B5 | RED | Write test: `test_paginar_contribuyentes_sql_placeholders` | `tests/unit/test_pagination.py` | — | Test verifies SQL construccion |
| B6 | RED | Write test: `test_paginar_contribuyentes_paginacion_completa` | `tests/unit/test_pagination.py` | — | Test verifies 3-page iteration |
| B7 | RED | Write test: `test_paginar_contribuyentes_resultado_vacio_termina` | `tests/unit/test_pagination.py` | — | Test verifies break on empty |

**GREEN phase for all B tests**: Run all tests → all pass immediately (code exists)

## Grupo C: client_adapter.py (3 tasks)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| C1 | RED | Write test: `test_agent_buscar_delega_a_paginar` | `tests/unit/test_client_adapter.py` | — | Test verifies delegation |
| C2 | RED | Write test: `test_agent_obtener_datos_delega` | `tests/unit/test_client_adapter.py` | — | Test verifies obtener_datos |
| C3 | RED | Write test: `test_agent_close_no_op` | `tests/unit/test_client_adapter.py` | — | Test verifies close |

**GREEN phase for all C tests**: Run all tests → all pass immediately (code exists)

## Grupo D: tasks/analisis_task.py (5 tasks)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| D1 | RED | Write test: `test_analizar_proceso_happy_path` | `tests/unit/test_analisis_task.py` | — | Test verifies full loop with NITs |
| D2 | RED | Write test: `test_analizar_proceso_con_error_por_nit` | `tests/unit/test_analisis_task.py` | — | Test verifies error handling per NIT |
| D3 | RED | Write test: `test_analizar_proceso_sin_nits` | `tests/unit/test_analisis_task.py` | — | Test verifies 0 rows |
| D4 | RED | Write test: `test_analizar_proceso_estado_final_completado` | `tests/unit/test_analisis_task.py` | — | Test verifies COMPLETADO state |
| D5 | RED | Write test: `test_analizar_proceso_estado_final_error` | `tests/unit/test_analisis_task.py` | — | Test verifies ERROR state on failures |

**GREEN phase for all D tests**: Run all tests → all pass immediately (code exists)

## Grupo E: config.py (3 tasks, adicion a test_config.py existente)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| E1 | RED | Write test: `test_settings_mcp_vars_defaults` | `tests/unit/test_config.py` | — | Test verifies defaults |
| E2 | RED | Write test: `test_settings_mcp_vars_from_env` | `tests/unit/test_config.py` | — | Test verifies env reading |
| E3 | RED | Write test: `test_settings_mcp_rechaza_changeme` | `tests/unit/test_config.py` | — | Test verifies validator |

**GREEN phase for all E tests**: Run all tests → all pass immediately (code exists)

## Grupo F: classify.py (2 tasks, adicion a test_classify.py existente)

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| F1 | RED | Write test: `test_omiso_por_keyword_en_razon` | `tests/unit/test_classify.py` | — | Test "no declaró" keyword |
| F2 | RED | Write test: `test_inexacto_score_exacto_30` | `tests/unit/test_classify.py` | — | Test boundary score=30 |

**GREEN phase for all F tests**: Run all tests → all pass immediately (code exists)

---

## Grupo P: REFACTOR phase

Tareas de limpieza post-tests:

| # | Phase | Task | File(s) | Depends On | Verification |
|---|-------|------|---------|------------|--------------|
| P1 | REFACTOR | Run lint + format | all new test files | Todos los tests GREEN | ruff check --fix, ruff format |
| P2 | REFACTOR | Run full test suite | tests/unit/ | P1 | 116 + X tests passing |
| P3 | REFACTOR | Measure coverage delta | tests/unit/ | P2 | `--cov=microservice --cov-report=term` |

---

**Total: 25 RED tasks, estimated ~25 new tests, targeting +8-12% coverage increase.**

# Proposal: Adaptar SRF y orquestador a metodologia real

## Intent

Adaptar `crosscheck_service.py` (SRF) y `orquestar_proceso.py` para que trabajen con los 4 nuevos tipos de candidatos (OMISO_CONOCIDO, OMISO_DESCONOCIDO, INEXACTO_CIIU, INEXACTO_RETENCIONES) y parametrizar el periodo fiscal.

## Scope

- **In scope**:
  - `crosscheck_service.py`: `clasificar_por_datos()` acepta items de los nuevos tipos; `extraer_inconsistencias()` detecta CIIU y retenciones; `calcular_srf()` incorpora nuevos pesos
  - `orquestar_proceso.py`: parametrizar `periodo` (ya no hardcodeado "2024")
- **Out of scope**:
  - Ingesta DIAN (APEX)
  - Tests nuevos (se actualizan existentes)

## Affected Components

- `domain/services/crosscheck_service.py`
- `application/use_cases/orquestar_proceso.py`
- `tests/unit/test_crosscheck.py`
- `tests/unit/test_orchestrator.py`

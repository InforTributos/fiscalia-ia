---
name: fiscal-domain
description: Use when answering questions about ICA fiscal domain, the SRF scoring system, taxpayer classification (omiso/exacto/inexacto), process states, agents (AGT-00 to AGT-05), or any business-domain-specific logic.
---

# Fiscal Domain — FiscalIA

## ICA Tax Context
- **Impuesto de Industria y Comercio**: Municipal tax on commercial, industrial, and service activities in Colombia
- **Periodicity**: Bimonthly or monthly depending on income
- **Rate**: Varies by municipality and CIIU code (municipal agreement)
- **Tax base**: Gross income
- **Legal framework**: Ley 14 de 1983, Ley 1819 de 2016, Ley 2277 de 2022

## Taxpayer Classification
After MCP filtering, NITs fall into 3 groups:

| Group | Meaning | Action |
|---|---|---|
| **Omiso** | Did not file ICA returns | LLM generates fiscal gap + explanation |
| **Exacto** | Filed correctly | Discarded, no further analysis |
| **Inexacto** | Filed with errors/inconsistencies | LLM generates findings + SRF + explanation |

## SRF — Fiscal Risk Score (0-100)

| Component | Weight |
|---|---|
| Exogenous income vs ICA declared | 35% |
| Filing delinquency | 20% |
| CIIU rate discrepancy | 25% |
| RUES vs registry status | 20% |

Risk levels: BAJO (<40), MEDIO (40-70), ALTO (>70)

## Agents (AI-DLC Hat-Based)
- **AGT-00 Orchestrator**: `application/use_cases/orquestar_proceso.py`
- **AGT-01 CrossCheck**: `domain/services/crosscheck_service.py` — SRF calculation, classification, inconsistency extraction
- **AGT-02 OmisosDetect**: `crosscheck_service.clasificar_por_datos()`
- **AGT-03 InconsistencyAnalyzer**: `domain/services/inconsistency_service.py` — risk level
- **AGT-05 MCP Client**: `infrastructure/mcp/oracle_adapter.py` — MCP stdio connection

## Process States
PENDIENTE → PREFILTRANDO → PREFILTRADO_COMPLETADO → EN_COLA → EN_PROCESO → COMPLETADO | ERROR | INTERRUMPIDO

## HITL (Human-in-the-Loop)
The final decision ALWAYS rests with the civil servant. AI generates findings, SRF, and recommendations.

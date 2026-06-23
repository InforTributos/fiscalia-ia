# FiscalIA — Agents

Esta carpeta es un alias/guía para la configuración de agentes OpenCode.

La configuración real está en `.opencode/`. Este archivo resume lo que hay disponible.

## Agentes

| Nombre | Descripción | Cómo invocar | Ubicación real |
|---|---|---|---|
| **fiscal-reviewer** | Revisor de código: verifica arquitectura hexagonal, convenciones y seguridad | `@fiscal-reviewer` en el chat | `.opencode/agents/fiscal-reviewer.md` |
| **domain-expert** | Experto en dominio ICA: SRF, clasificación, MCP, agentes | `@domain-expert` en el chat | `.opencode/agents/domain-expert.md` |

## Skills (auto-detectan cuándo activarse)

| Skill | Cuándo se activa | Ubicación real |
|---|---|---|
| **fiscal-domain** | Palabras: fiscalización, ICA, SRF, contribuyente, CIIU | `.opencode/skills/fiscal-domain/SKILL.md` |
| **hexagonal-arch** | Palabras: arquitectura, hexagonal, domain, ports | `.opencode/skills/hexagonal-arch/SKILL.md` |
| **testing-conventions** | Palabras: test, pytest, mock, fixture, coverage | `.opencode/skills/testing-conventions/SKILL.md` |
| **error-handling** | Palabras: error, excepción, FiscalIAError, handler | `.opencode/skills/error-handling/SKILL.md` |
| **mcp-contract** | Palabras: MCP, Oracle, buscar_contribuyentes | `.opencode/skills/mcp-contract/SKILL.md` |

## Comandos

| Comando | Qué hace | Cómo usarlo | Ubicación real |
|---|---|---|---|
| `/test` | Ejecuta tests unitarios | `/test` o `/test test_mi_caso.py` | `.opencode/commands/test.md` |
| `/lint` | Verifica linting | `/lint` | `.opencode/commands/lint.md` |
| `/coverage` | Reporte de cobertura | `/coverage` | `.opencode/commands/coverage.md` |
| `/dev` | Inicia servidor de desarrollo | `/dev` | `.opencode/commands/dev.md` |
| `/analyze` | Analiza un NIT | `/analyze 9003189639` | `.opencode/commands/analyze.md` |

## References (contexto adicional vía `@`)

```
@docs    → docs/ (arquitectura, endpoints, configuración)
@domain  → .ai-dlc/knowledge/ (dominio ICA, agentes, SRF)
@plans   → Planes de trabajo fiscalIA/ (plan V1 y V2.1)
```

## Configuración

Ver `opencode.json` en la raíz del proyecto para la configuración completa.

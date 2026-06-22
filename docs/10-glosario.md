# Glosario — FiscalIA

## A

| Término | Definición |
|---|---|
| **AGT** | Agent. Cada uno de los agentes de IA que componen FiscalIA (AGT-00 a AGT-05). Inspirado en la metodología AI-DLC Hat-Based. |
| **AI-DLC** | AI-Driven Development Lifecycle. Metodología de desarrollo de software asistido por IA creada por Next AI Tech LLC. |
| **APEX** | Oracle Application Express. Plataforma low-code de Oracle para desarrollo web. Usada como frontend de Taxation Smart. |
| **asyncpg** | Librería Python asíncrona para conexión a PostgreSQL. Usada como driver principal de base de datos. |

## C

| Término | Definición |
|---|---|
| **CIIU** | Clasificación Industrial Internacional Uniforme. Código que identifica la actividad económica de un contribuyente. |
| **Claude API** | API de Anthropic para acceder a Claude. Provider Tier 1 en FiscalIA. |
| **Confecámaras** | Red de cámaras de comercio colombianas. Administra el RUES. |

## D

| Término | Definición |
|---|---|
| **DIAN** | Dirección de Impuestos y Aduanas Nacionales. Autoridad tributaria nacional de Colombia. |
| **DIAN Exógena** | Información sobre operaciones económicas reportada por terceros a la DIAN. Fuente para detectar subregistro de ingresos ICA. |

## E

| Término | Definición |
|---|---|
| **Exógena municipal** | Reporte anual que los contribuyentes presentan al municipio con detalle de ingresos. |

## F

| Término | Definición |
|---|---|
| **Factory** | Patrón de diseño para crear objetos. En tests, genera datos sintéticos vía factory-boy. |
| **FastMCP** | Librería Python para implementar clientes MCP (Model Context Protocol). Usada en `infrastructure/mcp/`. |
| **FiscalIAError** | Jerarquía de excepciones del dominio. Cada tipo tiene código HTTP asociado. |

## H

| Término | Definición |
|---|---|
| **Hat** | Sombrero. Rol que asume un agente IA en la metodología AI-DLC. Ejemplos: Planner, Builder, Reviewer. |
| **HITL** | Human-in-the-Loop. Control obligatorio donde el funcionario revisa las decisiones antes de ejecutarlas. |

## I

| Término | Definición |
|---|---|
| **ICA** | Impuesto de Industria y Comercio. Principal tributo municipal colombiano. |
| **Intent** | AI-DLC: meta de alto nivel que guía el desarrollo. |

## L

| Término | Definición |
|---|---|
| **LLM** | Large Language Model. Modelo de lenguaje de gran escala (Claude, GPT, Qwen, etc.). |
| **LLMProvider** | ABC en `domain/ports/llm_port.py`. Interfaz común para todos los proveedores LLM. |
| **LLMService** | Implementación en `infrastructure/llm/llm_service.py`. Orquesta fallback chain con tenacity. |

## M

| Término | Definición |
|---|---|
| **MCP** | Model Context Protocol. Protocolo estándar para comunicación entre agentes y herramientas. |
| **MCP Client** | Cliente MCP vía stdio implementado en `infrastructure/mcp/oracle_adapter.py`. |

## N

| Término | Definición |
|---|---|
| **Next AI Tech LLC** | Empresa creadora de la metodología AI-DLC Hat-Based. |

## O

| Término | Definición |
|---|---|
| **OCI** | Oracle Cloud Infrastructure. Plataforma cloud de Oracle. |
| **OCI Container Instance** | Servicio de OCI para ejecutar contenedores Docker. |

## P

| Término | Definición |
|---|---|
| **PostgresProcesoRepo** | Repositorio concreto en `infrastructure/persistence/repositorio_proceso.py`. Implementa `ProcesoRepo`. |
| **Ports & Adapters** | Estilo arquitectónico hexagonal. Los puertos son interfaces (ABCs), los adapters son implementaciones concretas. |

## R

| Término | Definición |
|---|---|
| **RUES** | Registro Único Empresarial y Social. Directorio nacional de empresas administrado por Confecámaras. |
| **ruff** | Linter y formateador de Python. |

## S

| Término | Definición |
|---|---|
| **SRF** | Score de Riesgo Fiscal. Indicador 0-100 con 4 componentes: exógena (35%), tarifa CIIU (25%), omisión (20%), RUES (20%). |

## T

| Término | Definición |
|---|---|
| **Taxation Smart** | Sistema tributario municipal de Informática y Tributos S.A.S. FiscalIA es un módulo dentro de este sistema. |
| **tenacity** | Librería Python para retry con backoff. Usada en `LLMService` y `tasks/retry.py`. |
| **Temperature** | Parámetro del LLM que controla la creatividad. En FiscalIA se usa 0.1 (bajo). |

## U

| Término | Definición |
|---|---|
| **Unit** | AI-DLC: paquete de trabajo discreto dentro de un Intent. |

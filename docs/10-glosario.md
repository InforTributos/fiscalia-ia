# Glosario — FiscalIA

## A

| Término | Definición |
|---|---|
| **AGT** | Agent. Cada uno de los agentes de IA que componen FiscalIA (AGT-00 a AGT-04). Inspirado en la metodología AI-DLC Hat-Based. |
| **AI-DLC** | AI-Driven Development Lifecycle. Metodología de desarrollo de software asistido por IA creada por Next AI Tech LLC. Define hats, intents, units, bolts y quality gates. |
| **APEX** | Oracle Application Express. Plataforma low-code de Oracle para desarrollo web. Usada como frontend de Taxation Smart y FiscalIA. |
| **AHOTL** | Autonomous Human-on-the-Loop. Modo donde el sistema opera autónomamente y el humano recibe actualizaciones periódicas. |

## C

| Término | Definición |
|---|---|
| **CIIU** | Clasificación Industrial Internacional Uniforme. Código que identifica la actividad económica de un contribuyente. En Colombia, usado por DIAN y municipios para ICA. |
| **Claude API** | API de Anthropic para acceder al modelo claude-sonnet-4. Usado por FiscalIA para generar explicaciones en lenguaje natural. |
| **Confecámaras** | Red de cámaras de comercio colombianas. Administra el RUES (Registro Único Empresarial). |

## D

| Término | Definición |
|---|---|
| **DIAN** | Dirección de Impuestos y Aduanas Nacionales. Autoridad tributaria nacional de Colombia. |
| **DIAN Exógena** | Información sobre operaciones económicas reportada por terceros a la DIAN (formatos 1001, 1007). Fuente principal para detectar subregistro de ingresos ICA. |
| **DTO** | Data Transfer Object. Objeto que transfiere datos entre capas, sin lógica de negocio. |

## E

| Término | Definición |
|---|---|
| **Exógena municipal** | Reporte anual que los contribuyentes presentan al municipio con detalle de ingresos por tercero y CIIU. |
| **Expediente** | Conjunto de documentos y actuaciones asociados a la fiscalización de un contribuyente específico. |

## F

| Término | Definición |
|---|---|
| **Firmapp** | Solución de firma digital de Informática y Tributos S.A.S. |
| **FISCALIA** | Nombre del módulo de fiscalización ICA con IA. |

## H

| Término | Definición |
|---|---|
| **Hat** | Sombrero. Rol que asume un agente IA en la metodología AI-DLC. Ejemplos: Planner, Builder, Reviewer. |
| **HITL** | Human-in-the-Loop. Control obligatorio donde el funcionario revisa y aprueba las decisiones del agente IA antes de ejecutarlas. |

## I

| Término | Definición |
|---|---|
| **ICA** | Impuesto de Industria y Comercio. Principal tributo municipal colombiano. Grava las actividades comerciales, industriales y de servicios. |
| **Información exógena** | Datos de operaciones con terceros que los contribuyentes reportan anualmente a la DIAN o al municipio. |
| **Intent** | AI-DLC: meta de alto nivel que guía el desarrollo (ej: "Implementar microservicio OCI"). |

## L

| Término | Definición |
|---|---|
| **LangGraph** | Framework para orquestar agentes IA como grafos. Usado en el microservicio para coordinar AGT-01 y AGT-03. |
| **litellm** | Librería Python que permite llamar a 100+ proveedores LLM con la misma interfaz. Usada en FiscalIA para hacer el LLM agnóstico. |
| **LLM** | Large Language Model. Modelo de lenguaje de gran escala (Claude, GPT, Llama, etc.). |

## N

| Término | Definición |
|---|---|
| **Next AI Tech LLC** | Empresa del autor JC Herrera Reyes. Creadora de la metodología AI-DLC Hat-Based. |

## O

| Término | Definición |
|---|---|
| **OCI** | Oracle Cloud Infrastructure. Plataforma cloud de Oracle donde se despliegan Taxation Smart y FiscalIA. |
| **OCI Container Instance** | Servicio de OCI para ejecutar contenedores Docker sin gestionar Kubernetes. |
| **OHOTL** | On-Human-On-The-Loop. Modo donde el humano está disponible para intervenir pero la IA toma iniciativa. |

## P

| Término | Definición |
|---|---|
| **PL/SQL** | Procedural Language / Structured Query Language. Lenguaje procedural de Oracle. Toda la lógica de negocio de Taxation Smart está en PL/SQL. |
| **Ports & Adapters** | Estilo arquitectónico hexagonal. Los puertos son interfaces (contratos), los adapters son implementaciones concretas. |

## R

| Término | Definición |
|---|---|
| **RBAC** | Role-Based Access Control. Control de acceso basado en roles: FISCAL_ADMIN, FISCAL_SUPERVISOR, FISCAL_ANALISTA. |
| **REST Data Source** | Recurso de Oracle APEX para consumir APIs REST externas. |
| **RUES** | Registro Único Empresarial y Social. Directorio nacional de empresas registradas en Colombia, administrado por Confecámaras. |

## S

| Término | Definición |
|---|---|
| **SRF** | Score de Riesgo Fiscal. Indicador 0-100 que representa la probabilidad estimada de incumplimiento tributario. Componentes: exógena (35%), tarifa CIIU (25%), omisión (20%), RUES (20%). |
| **Subdeclaración** | Declarar menos ingresos de los reales. Detectado cruzando exógena vs ICA. |

## T

| Término | Definición |
|---|---|
| **Taxation Smart** | Sistema tributario municipal de Informática y Tributos S.A.S. FiscalIA es un módulo dentro de este sistema. |
| **TDE** | Transparent Data Encryption. Cifrado a nivel de base de datos Oracle. |
| **Temperature** | Parámetro del LLM que controla la creatividad. En FiscalIA se usa 0.1 (bajo). |

## U

| Término | Definición |
|---|---|
| **Unit** | AI-DLC: paquete de trabajo discreto dentro de un Intent. |
| **UTL_MATCH** | Paquete Oracle con funciones de comparación de strings. Usado para fuzzy matching de razones sociales. |

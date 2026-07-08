# Propuesta de Desarrollo — Sistema de Fiscalización Inteligente de ICA

## 1. Contexto y Problema a Resolver

La Secretaría de Hacienda de Valledupar tiene la responsabilidad de fiscalizar el correcto pago del Impuesto de Industria y Comercio (ICA) por parte de miles de contribuyentes del municipio. Hoy en día, identificar quién no ha declarado, quién declaró de menos o quién aplicó una tarifa incorrecta es un proceso que depende en gran medida de la revisión manual, cruzando información dispersa entre distintas fuentes (declaraciones de ICA, información exógena de la DIAN, y el registro de cámara de comercio).

Este proceso manual tiene tres limitaciones importantes:

- **Es lento:** revisar contribuyente por contribuyente toma tiempo que el equipo de fiscalización no siempre tiene.
- **Es difícil de priorizar:** sin un criterio objetivo, es complicado decidir a qué contribuyentes revisar primero.
- **Depende de la experiencia individual:** el conocimiento para detectar inconsistencias está en la cabeza de los funcionarios más experimentados, no en un sistema que lo replique de forma consistente.

## 2. Objetivo de la Propuesta

Desarrollar **FiscalIA**, un sistema de apoyo a la fiscalización que automatiza el cruce de información entre las distintas fuentes de datos del municipio, calcula un puntaje objetivo de riesgo fiscal para cada contribuyente, y genera explicaciones claras en lenguaje natural sobre los hallazgos — para que el equipo de fiscalización pueda enfocar su tiempo en los casos que realmente lo ameritan, con criterios objetivos y trazables.

FiscalIA **no reemplaza al funcionario fiscalizador**. Es una herramienta que hace el trabajo pesado de recopilar, cruzar y analizar información, y le entrega al funcionario un resumen listo para su revisión y decisión final.

## 3. ¿Cómo Funciona? (Visión General)

El sistema se integra directamente con **Oracle APEX**, la plataforma que la Secretaría de Hacienda ya usa hoy (Taxation Smart), por lo que no representa una herramienta nueva y aislada, sino una capacidad adicional dentro del flujo de trabajo actual del funcionario.

El proceso, en términos simples, sigue estos pasos:

1. **Selección de contribuyentes a revisar** — el funcionario define criterios (por ejemplo: período fiscal, tipo de actividad económica, régimen tributario) desde la plataforma APEX.
2. **Recolección automática de información** — el sistema busca y reúne, para cada contribuyente, sus declaraciones de ICA y la información reportada a la DIAN (exógena). El cruce adicional con el registro mercantil (RUES/Cámara de Comercio) ya cuenta con una integración a nivel de API en la plataforma APEX del equipo de Hacienda. El sistema utilizará esta conexión para obtener el estado mercantil de cada contribuyente como insumo para el cálculo del SRF.
3. **Cruce y análisis de la información** — el sistema compara estas fuentes entre sí y calcula un **Score de Riesgo Fiscal (SRF)**, un puntaje de 0 a 100 que resume qué tan probable es que exista una irregularidad, junto con el tipo de irregularidad detectada (contribuyente que no declaró, que declaró de menos, que aplicó una tarifa equivocada, etc.).
4. **Explicación en lenguaje natural** — aquí es donde entra la Inteligencia Artificial (ver sección 4): el sistema no solo entrega un número, sino una explicación clara y en español corriente de por qué ese contribuyente tiene ese puntaje y qué se recomienda revisar.
5. **Entrega de resultados al funcionario** — todo el análisis queda disponible directamente en APEX, listo para que el fiscalizador lo revise y decida los siguientes pasos (esto último — la generación de actos formales como requerimientos o emplazamientos — queda fuera del alcance de esta primera versión y se evaluará como una fase futura).

> **Nota sobre el estado actual de este flujo:** hoy el análisis completo (recolección, cruce, cálculo de SRF y explicación con IA) ya funciona de punta a punta para **la consulta de un contribuyente puntual**. La conexión que permite ejecutar este mismo flujo de forma **masiva y automática sobre un lote completo de contribuyentes** (pasos 1 a 3, cuando se seleccionan muchos contribuyentes a la vez con un criterio general) se encuentra en su etapa final de integración. Ver el detalle en la sección 6.

## 4. El Rol de la Inteligencia Artificial

Uno de los componentes centrales de esta propuesta es el uso de Inteligencia Artificial (modelos de lenguaje, la misma familia de tecnología detrás de asistentes como ChatGPT o Claude) para una tarea muy específica: **traducir datos y cálculos técnicos en explicaciones que cualquier funcionario pueda entender, sin necesitar conocimientos de análisis de datos**.

### ¿Qué hace exactamente la IA en este sistema?

- **Explica el puntaje de riesgo:** en lugar de mostrar solo "SRF: 78/100", la IA redacta una explicación como "Este contribuyente presenta un riesgo alto principalmente porque reportó a la DIAN ingresos muy superiores a los declarados en ICA, y su tarifa aplicada no corresponde a su actividad económica registrada."
- **Describe las inconsistencias encontradas:** cuando el sistema detecta, por ejemplo, que un contribuyente subdeclaró ingresos, aplicó una exención sin soporte, o declaró base gravable en cero de forma injustificada, la IA redacta el hallazgo en un lenguaje claro, con contexto normativo cuando aplica.
- **Sugiere una recomendación de acción:** una orientación inicial sobre qué tipo de revisión o requerimiento podría aplicar, siempre como insumo para que el funcionario decida — no como una decisión automática.

### ¿Qué NO hace la IA?

Es igual de importante ser claros en esto: la Inteligencia Artificial **no decide, no sanciona ni emite ningún acto administrativo por sí sola**. Su función se limita a **generar explicaciones y resúmenes** a partir de datos y cálculos que ya fueron determinados por reglas de negocio claras y verificables (el cálculo del puntaje de riesgo, por ejemplo, no lo hace la IA — lo hace una lógica fija y auditable; la IA solo lo explica en palabras). La decisión final siempre queda en manos del equipo de fiscalización de la Secretaría de Hacienda.

### Confiabilidad: ¿qué pasa si el proveedor de IA falla?

Para que el sistema no dependa de un único proveedor de tecnología (lo cual sería un riesgo operativo), se diseñó un **esquema de respaldo en cascada**: si el proveedor principal de IA no está disponible en un momento dado, el sistema automáticamente intenta con un segundo proveedor, y si ese también falla, con un tercero. Esto garantiza continuidad del servicio incluso ante fallas externas, sin intervención manual. En el caso extremo de que ningún proveedor esté disponible, el sistema no se detiene: simplemente entrega el resultado del análisis sin la explicación en lenguaje natural, y continúa procesando el resto de los contribuyentes.

## 5. Beneficios para la Secretaría de Hacienda

| Beneficio | Descripción |
|---|---|
| **Priorización objetiva** | El equipo de fiscalización sabe, con un criterio numérico y consistente, a qué contribuyentes revisar primero. |
| **Ahorro de tiempo** | El cruce de información entre fuentes, que hoy es manual, se hace de forma automática. |
| **Explicaciones listas para usar** | No se requiere que el funcionario interprete datos crudos; la IA entrega el análisis en lenguaje natural. |
| **Trazabilidad** | Cada análisis queda registrado, con fecha, criterios usados y resultado — auditable en cualquier momento. |
| **Sin cambiar de herramienta** | Se integra al sistema APEX que el equipo ya usa hoy, sin curva de aprendizaje adicional. |
| **Continuidad garantizada** | El esquema de respaldo entre proveedores de IA evita que una falla externa detenga la operación. |
| **Integración con infraestructura actual** | Aprovecha la conexión API existente con APEX para RUES/Cámara de Comercio, asegurando trazabilidad de datos. |

## 6. Estado Actual del Desarrollo

El desarrollo ha avanzado en fases incrementales. A la fecha de este informe:

| Fase | Contenido | Estado |
|---|---|---|
| Fase 1 | Base del sistema y conexión con la base de datos de procesos | ✅ Completada |
| Fase 2 | Lógica de negocio: cálculo del puntaje de riesgo | ✅ Completada |
| Fase 3 | Puntos de integración con APEX (consultar, iniciar y revisar análisis) | ✅ Completada |
| Fase 4 | Optimización de rendimiento y manejo de errores | ✅ Completada |
| Fase 5 | Motor de Inteligencia Artificial | ✅ Completada |
| Fase 6 | Pruebas y quality gate | ✅ Completada |

El sistema cuenta actualmente con **más de 115 pruebas automatizadas** que validan su correcto funcionamiento, y ha superado las validaciones de calidad de código establecidas para el proyecto.

> **Nota sobre la Fase 4:** el análisis individual de un contribuyente (consulta puntual) ya funciona de extremo a extremo con las fuentes de ICA y exógena DIAN. Dos elementos de esta fase están pendientes de cerrar:
> 1. La ejecución de este mismo análisis de forma **masiva y automática** sobre un lote completo de contribuyentes seleccionados por criterio (por ejemplo, "todos los del régimen común del sector comercio") — es un ajuste acotado sobre trabajo ya construido, no un desarrollo nuevo desde cero.
> 2. **Conectar el cruce con RUES/Cámara de Comercio al cálculo del SRF** — la integración API ya está disponible en APEX. El componente del SRF que evalúa el estado mercantil (peso 20%) utilizará esta conexión. Pendiente definir con el equipo de Hacienda la periodicidad de actualización de los datos de RUES para asegurar información vigente en cada proceso de fiscalización.

## 7. Pendientes que requieren definición de la Secretaría de Hacienda

| Pendiente | Detalle | Responsable |
|---|---|---|
| **Actualización de datos RUES en APEX** | Definir la periodicidad con que se actualizarán los datos de estado mercantil (RUES) en la plataforma APEX: ¿diaria, semanal, mensual? Esta información alimenta el componente "Estado RUES" del Score de Riesgo Fiscal (peso 20%). Sin datos vigentes, el componente no refleja la situación actual del contribuyente. | Secretaría de Hacienda / equipo APEX |
| **Consumir endpoint RUES desde microservicio** | Implementar en el microservicio la llamada al endpoint de RUES para extraer el estado mercantil y alimentar el cálculo del SRF. | Informática y Tributos S.A.S. |

## 8. Pendientes de desarrollo interno

| Pendiente | Responsable |
|---|---|
| **Conectar "Convertir en consistente" a "Completado"** | Informática y Tributos S.A.S. — La integración API ya está disponible. Pendiente consumir el endpoint de RUES desde el microservicio. |

## 9. Pendientes para la puesta en producción

| Pendiente | Responsable |
|---|---|
| **Habilitación del acceso a la información fiscal real (Oracle) en el ambiente de producción** | Equipo APEX / Infraestructura del municipio |
| **Aprovisionamiento del servidor donde correrá el sistema** | Equipo de Infraestructura |
| **Activación de las credenciales de los proveedores de IA para el ambiente productivo** | Definición conjunta |

## 10. Próximos Pasos Propuestos

1. **Validar esta propuesta con la Secretaría de Hacienda** y recoger observaciones.
2. **Definir con el equipo de Hacienda la periodicidad de actualización de datos RUES en APEX** y **consumir el endpoint de estado mercantil desde el microservicio** para alimentar el cálculo del SRF.
3. **Coordinar con el equipo de infraestructura** la disponibilidad del ambiente de producción y el acceso a la información fiscal real.
4. **Ejecutar una fase de pruebas piloto** con un grupo controlado de contribuyentes, antes de habilitar el uso masivo.
5. **Evaluar, como una fase posterior**, la generación asistida de actos formales (requerimientos, emplazamientos), que hoy queda deliberadamente fuera del alcance para asegurar primero la solidez del análisis y la explicación.

---
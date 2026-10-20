# Cómo se han hecho las certificaciones reales

Referencia para el desarrollo del Copiloto. Recopila las certificaciones de bugs y brechas hechas en Beyond Health entre agosto y octubre de 2026.

**Idea central: ninguna certificación se parece a otra.** Cambian los insumos, la forma de obtener datos, el canal de ejecución, el número de casos, la redacción y la evidencia. El sistema debe adaptarse a cada caso y no imponer un único camino.

> Este documento no contiene datos personales reales. Las cédulas, nombres y contratos de las certificaciones originales se omitieron a propósito.

---

## 1. Catálogo de certificaciones

| Certificación | Tipo | Módulo | Insumos | Cómo se obtuvieron los datos | Canal de ejecución | Casos |
|---|---|---|---|---|---|---|
| Exclusión de beneficiario (AFI-003) | Brecha | Afiliaciones – Novedades | Documento de requerimiento (451020), anexo de reglas de validación | Pedidos a un compañero (titulares y beneficiarios con contrato activo y sin fecha fin) | Pantalla de Novedades | 3 de frontera: antes, igual y después de la fecha de inicio de la IPS |
| Terminación de contrato | Brecha | Afiliaciones – Novedades | Misma lógica de fechas que la anterior | Pedidos a un compañero | Pantalla de Novedades | 6: tres con beneficiarios y tres sin beneficiarios |
| Brecha 979 – Incapacidad retroactiva | Brecha | Incapacidades | Documento de requerimiento | Buscados en un reporte `.txt` delimitado por `\|` | Pantalla de Incapacidades | 5: tres tipos que deben rechazar, uno de control y uno fuera de alcance (Licencia Parto Normal) |
| Bug 173292 – Semanas de cotización | Bug | Incapacidades – Análisis de empleadores | Prueba unitaria del desarrollador (CO-FR-VRA-02), historial de TFS | El mismo caso del desarrollador | Pantalla de Incapacidades | 1, comparando antes y después (2 líneas de cotización → 4) |
| Bug 173910 – Cambio fecha inicio IPS | Bug | Afiliaciones – Novedades | Historial de TFS, prueba unitaria | Afiliado del caso reportado, ya corregido en BD: se hizo un intento nuevo | Pantalla de Novedades (el cargue por archivo SAT falló) | 2: negativo y de control |
| Bug 174268 – Cargue masivo PILA (tipo de documento PC) | Bug | Recaudo – Cargue de aportes | Correo de asignación, prueba unitaria | Planilla enviada por la EPS | Archivo `.zip` (`AAAAMMDD`) en carpeta compartida → cargue → consignación → punteo → validación de planilla | 1 flujo completo |
| Corrección 4023 (Brecha 980) | Bug | Recaudo – Novedades de corrección | Respuesta al caso Aranda, nota de fábrica, script SQL | Registros del caso | Proceso batch; la evidencia del desarrollador era solo una consulta SQL | 1 |
| Bug 161582 – Modificar cotizante | Bug | Recaudo – Corrección 4023 | Historial de TFS con **dos hallazgos distintos** en el mismo ítem | Afiliado del caso | Pantalla | 1 (se certificó solo el segundo hallazgo) |
| Bug 173200 – Titular sin régimen | Bug | Afiliaciones – Contratos POS (inclusión de beneficiario) | Documento de evidencias (16 imágenes) | Afiliados reales del ambiente | Pantalla de Novedades + consulta de Personas y Tramos | 2: régimen Contributivo y régimen Subsidiado |
| Bug 174374 – Archivo plano R1 (BDUA) | Bug | BDUA – Generación de archivos | Historial de TFS | Registros creados a propósito (duplicados con distinto tipo de documento) | Proceso de generación de archivo | **1** (el analista rechazó los casos de regresión extra) |
| Brecha 295 – Movilidad subsidiado | Brecha | Afiliaciones – Movilidad | 2 documentos `.doc`, Excel de 12 casos, **correo del cliente con inconsistencias** | Los del plan original | Pantalla | 12 casos del plan; se confirmó una sola causa raíz |
| Cargue histórico subsidiados | Brecha | Afiliaciones – Cargues | Casos ya escritos (se mejoró la redacción) | — | Proceso + log descargable | 2: lógica de negocio y monitoreo/log |
| Brecha 990 – Régimen por tramos | Brecha | Servicio de contrato/cobertura (API) | Documento + **código PL/SQL** (excepcional) + certificación anterior (960) como ejemplo | Usuarios reales del ambiente buscados uno por uno según el patrón de tramos | **SoapUI, request REST con cuerpo JSON** (no SOAP/XML) | 12: seis de titular y seis de beneficiario (bajó desde 29) |

---

## 2. Qué varía y cómo

### 2.1 Insumos (lo que llega para certificar)

- **Documento de requerimiento** (`451020 – Modelo Análisis Producto Solicitud de Cambio`), a veces en `.doc` antiguo, con reglas y flujos numerados (ej. "paso 20a").
- **Prueba unitaria del desarrollador** (CO-FR-VRA-02). La información clave suele estar **en las imágenes incrustadas**, no en el texto.
- **Historial del ítem en TFS**: entradas fechadas de QA y fábrica, con changesets. Un mismo ítem puede tener varios hallazgos en el tiempo, y hay que identificar cuál se certifica.
- **Correo de asignación** con instrucciones de ejecución (rutas, carpetas, orden de pasos).
- **Respuesta a un caso Aranda** con medidas temporales y definitivas.
- **Lista de inconsistencias del cliente** sobre un plan ya ejecutado (Brecha 295).
- **Certificación anterior** usada como modelo de formato y redacción (ej. la 960 para la 990).
- **Código fuente**, solo en la 990.
- **Archivos de datos**: reportes `.txt` con `|`, planillas PILA, archivos planos R1 con codificación latin-1.

### 2.2 Obtención de datos de prueba

| Forma | Ejemplo |
|---|---|
| Pedirlos a un compañero o a fábrica | Exclusión de beneficiario |
| Buscarlos en un reporte grande | Brecha 979 (reporte `.txt`) |
| Usar el mismo caso del desarrollador o del reporte | Bugs 173292 y 173910 |
| Usar el archivo que envía el cliente | Bug 174268 (planilla PILA) |
| Buscar usuarios reales uno por uno en el ambiente | Brecha 990 |
| Crear registros a propósito | Bug 174374 (duplicados con TI vs RC) |

Problemas que se repitieron:
- El dato del caso **ya había sido corregido manualmente en BD**, así que se necesita un intento nuevo y no revisar el registro.
- El registro creado **no quedó como se esperaba** (otra fecha de nacimiento u otro número), lo que cambia la validez de la prueba.
- La fecha usada cae **fuera de la vigencia de la afiliación** y el resultado no prueba la regla (CP4, CP6 y CP12 de la 990).
- **Tramos anulados o cerrados** que siguen apareciendo vigentes por la fecha de cierre (990).

### 2.3 Canal de ejecución

- **Pantallas de Beyond Health**: Novedades, Incapacidades, Recaudo, Personas, Tramos de régimen.
- **SoapUI** con servicios **REST/JSON**. En la 990 el campo de régimen era `scope` y la fecha de validación iba como `"date": "AAAA-MM-DDT00:00:00"` al final del cuerpo; ambos se descubrieron durante la prueba.
- **Cargue de archivos** en una carpeta compartida con una convención de nombre, seguido de procesos en pantalla.
- **Procesos batch** que generan archivos (R1) o corrigen registros (4023).
- **Consultas a base de datos** cuando la evidencia del desarrollador es SQL.
- Hubo canales que **fallaron** y obligaron a cambiar de camino (cargue SAT → pantalla de Novedades).

### 2.4 Diseño de casos

| Patrón | Cuándo se usó |
|---|---|
| Un solo caso | Bug con un solo escenario (174374, 174268) |
| Negativo + control | Reproducir el bug y verificar que lo válido sigue funcionando (173910) |
| Antes y después | Replicar la prueba del desarrollador y mostrar el cambio (173292) |
| Frontera (antes / igual / después) | Reglas con comparación de fechas (exclusión de beneficiario) |
| Umbral numérico + control + fuera de alcance | Reglas con límite de días (979: 15 días hábiles con festivos) |
| Por escenario de negocio | Bug 173200: titular Contributivo vs. Subsidiado |
| Matriz por rol | Titular × beneficiario (990), con o sin beneficiarios (terminación de contrato) |
| Casos que vienen del cliente | Brecha 295: se cruzan los 12 casos con el texto literal del requerimiento |
| Lógica + monitoreo | Cargue histórico: el proceso y su log |

La cantidad de casos va de 1 a 12. En la 990 se empezó con 29 y se dejaron 12; en la exclusión de beneficiario se propusieron 5 y quedaron 3. **La primera propuesta casi siempre se recorta.**

### 2.5 Redacción del caso (cambia según la certificación)

1. **Formato corto** (preferido para bugs): *Título de la prueba*, *Descripción* y *Resultado esperado*.
2. **"Validar que…"**: *"Validar que el sistema rechace la exclusión de beneficiario cuando la fecha de efecto es anterior a la fecha de inicio de la IPS vigente."*
3. **"Al [acción], se ejecutan las siguientes validaciones"**: *"Al incluir un beneficiario en un contrato cuyo titular tiene el campo Régimen vacío en Personas, se ejecutan las siguientes validaciones: – … Resultado esperado: …"*
4. **"Consultar un…"** (servicios): *"Consultar un [titular/beneficiario] por el tipo de consulta 1, donde … Resultado esperado: …"*
5. **Hoja completa de la plantilla**: Objetivo, Precondiciones, Datos de entrada, Actividades y Pasos, cuando la plantilla lo exige.

Regla práctica: **copiar el estilo de la certificación modelo** que se tenga a mano o del plan existente, en vez de imponer uno.

### 2.6 Textos de evidencia

- **Por captura**: *"Captura 1 — Se muestra la CC del afiliado, con la Fecha Inicial … y la Fecha de Recepción …"*. *"Captura 2 — Se coloca en el campo … el valor …"*.
- **Estilo preferido de verbo**: *"Se le coloca la fecha…"* en lugar de *"Se evidencia…"*.
- **Paso a paso breve**: *"Se accede a Beyond Health, al apartado de novedades del contrato … y se genera la novedad … con fecha …"*.
- **Bloques de servicio** (990): condición del afiliado → consulta al servicio → resultado obtenido → observaciones. No se menciona la fecha de validación en los pasos si el caso no la especifica.
- **Antes y después** (173292): qué tomaba el sistema antes y qué toma ahora.
- Siempre se separa el resultado de la regla certificada del **ruido de otras validaciones** (mora en pagos, IPS fuera de red, causal del Decreto 1427, "el afiliado debe ser cotizante").

### 2.7 Resultados posibles

- **Certificado / Aprobado.**
- **Fallido**: a veces se reclasifica después de releer el requerimiento (CP-02 de exclusión de beneficiario: "mayor" vs. "menor" estricto en el paso 20a).
- **No concluyente / limitación de datos**: la evidencia no prueba el escenario (CP4, CP6 y CP12 de la 990).
- **Bug nuevo encontrado durante la certificación** (990: un solo tramo se devuelve sin importar la fecha; la fecha de cierre extiende la vigencia).
- **Observación que reencuadra el resultado** como comportamiento del sistema y no como error, por decisión del analista.
- **Brecha en la cobertura**: el caso prueba menos de lo que dice su título (173292 probó el tipo de trabajador, no múltiples empleadores).

### 2.8 Entregables

- **CO-FR-VRA-03**: encabezado con Proyecto, Fecha, ID Requerimiento, Nombre del Requerimiento, Cliente/Entidad, Aplicativo, Módulo, Tipo de Cambio, Descripción y Responsable QA; luego casos y evidencias.
- **Nota TFS**: muy corta, informativa, **sin explicar cómo se corrigió** y **sin negritas**. Ejemplo:
  `DD-MM-AAAA` *Se certifica el changeset N. Se ejecutan las pruebas correspondientes y se confirma el correcto funcionamiento. Certificación: Aprobado.*
- **Correo**: mínimo. *"Buen día: Se certifica el Bug N (Brecha M) – [nombre]. Certificación: Aprobado. Saludos."*
- A veces también: **respuesta al cliente** sobre un caso Aranda (con imágenes), **mensaje a fábrica** pidiendo un ajuste de datos con los campos de la novedad, o un **diagrama de decisión** del requerimiento.

---

## 3. Lecciones recurrentes

1. **No inventar datos.** Menos aún códigos bancarios o del sistema que deben cuadrar en el punteo. Si falta un dato, se pide.
2. **Marcar inferencias.** Distinguir lo que dice el documento de lo que se deduce (ej. la rama "sin acción" no especificada en la Brecha 295 se confirma con el líder).
3. **No cerrar el análisis sin la evidencia real.** Aunque exista una plantilla de un caso parecido.
4. **Verificar que el fix esté desplegado** en el ambiente antes de concluir que falla.
5. **Revisar residuos de la certificación anterior** en el Excel: títulos viejos, hojas de otro caso, módulo equivocado.
6. **Certificar el hallazgo correcto** cuando el ítem de TFS tiene varios.
7. **Revisar que el módulo y la descripción correspondan** al bug que se certifica y no al anterior.
8. **Revisión final antes de entregar**: casos "Certificado" sin observación cuando la evidencia no prueba el escenario, campos vacíos, contradicciones entre el estado y lo encontrado, y errores de redacción.
9. **Redacción corta.** Las correcciones más frecuentes del analista fueron "más corto", "menos específico" y "solo informativo".

---

## 4. Implicaciones para el Copiloto

Esto obliga a ajustar algunos supuestos de `SPEC.md` v2.0:

| Supuesto actual | Realidad | Ajuste |
|---|---|---|
| Ejecución por request **SOAP/XML** | La 990 fue **REST/JSON**; otras fueron por pantalla, archivo o batch | Plantillas de request para SOAP **y** REST/JSON. Cada caso declara su canal: `ui`, `soap`, `rest`, `file_upload`, `batch`, `db_query`. Solo los canales de servicio generan request |
| Siempre se pide la data a fábrica | La data llega de 6 formas distintas | La solicitud a fábrica es **opcional**. El paso 5 acepta cualquier origen o se salta |
| Variantes con tramos | Solo algunos módulos tienen tramos | Registros hijos opcionales por servicio (ya planteado) |
| Un formato de caso | Hay al menos 5 estilos | **Plantillas de redacción seleccionables**, más la opción de "imitar una certificación modelo" que el analista sube |
| Un formato de evidencia | Captura por captura, paso a paso, bloques de servicio, antes/después | Plantillas de evidencia seleccionables por certificación |
| Insumos: documento, descripción, reporte, código | También prueba unitaria con imágenes, historial de TFS, correos, lista de inconsistencias del cliente, certificación modelo | Más tipos de fuente, extracción de imágenes incrustadas y lectura de `.doc` antiguo |
| Resultado: pasa, falla, limitación de datos | También bug nuevo encontrado y brecha de cobertura | Agregar `new_defect` y un control de cobertura en la revisión (título vs. lo que prueba la evidencia) |
| Análisis automático de la respuesta | Solo aplica a servicios | En pantalla, archivo o batch, el analista registra el resultado y el sistema solo redacta |
| TFS como un solo hallazgo | Ítems con varios hallazgos | Al pegar el historial, el sistema identifica los hallazgos y pregunta cuál se certifica |

**Principio de diseño:** el flujo de 9 pasos es el máximo, no un camino obligatorio. Cada certificación activa solo los pasos que necesita: un bug con un solo caso por pantalla puede ir directo de contexto a caso, ejecución, evidencia y nota TFS.

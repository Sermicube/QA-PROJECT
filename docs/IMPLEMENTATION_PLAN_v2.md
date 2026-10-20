# Plan de implementación — Copiloto QA v2.0

Generado: 2026-10-08. Basado en `SPEC.md v2.0`.

---

## Contexto: qué hay implementado (base v1.1)

El código actual es la v1.1 con un flujo de 7 etapas (`context → ambiguities → testcases → testdata → execution → deliverables → closed`). Lo que existe es sólido en lo que toca:

| Módulo | Estado | Qué sirve para v2.0 |
|---|---|---|
| `core/` | Completo | Reutilizar todo tal cual |
| `llm/` | Completo | Reutilizar; agregar escáner de secretos |
| `users/` | Completo | Reutilizar todo |
| `certifications/` | Completo | Actualizar lista de etapas (7→10) |
| `context/` | Completo | Reutilizar extracción y ambigüedades; reemplazar criterios por reglas |
| `testcases/domain/linter.py` | Completo | Adaptar a `style.py` con reglas S01–S06 |
| `testdata/domain/filter.py` | Completo | Reutilizar el evaluador DSL de condiciones |
| `testdata/domain/dates.py` | Completo | Reutilizar; ampliar estrategias de fecha |
| `testdata/domain/assignment.py` | Completo | Reescribir para soportar reglas de riesgo |
| `evidence/domain/ocr.py` | Completo | Reutilizar tal cual |
| `deliverables/domain/excel_filler.py` | Completo | Adaptar a nuevo formato de campos (fields.yaml) |
| `metrics/` | Completo | Ampliar con nuevas métricas |

**Módulos nuevos necesarios:** `certformat/`, `datarequest/`, `soap/`, `analysis/`, `review/`.

---

## Fase 0 — Migración de base (v1.1 → v2.0)

**Objetivo:** adaptar la infraestructura existente al nuevo flujo sin romper lo que funciona.

### 0.1 Etapas de certificación

Archivo: `backend/app/certifications/models.py`

Cambiar `STAGE_ORDER` de:
```python
["context", "ambiguities", "testcases", "testdata", "execution", "deliverables", "closed"]
```
a:
```python
["context", "testcases", "format", "data_request", "assignment", "execution", "analysis", "documentation", "review", "closed"]
```

Migración Alembic: actualizar la columna `stage` para aceptar los nuevos valores.

### 0.2 Escáner de secretos en `llm/`

Archivo nuevo: `backend/app/llm/secrets_scanner.py`

```python
class SecretsScanner:
    def scan(self, text: str) -> list[SecretMatch]: ...
    def mask(self, text: str) -> tuple[str, int]: ...
```

Patrones: contraseñas (`password\s*=\s*\S+`), cadenas de conexión (`jdbc:`, `postgresql://`, `mongodb://`), tokens (Bearer, ghp_, sk-ant-), llaves privadas. Se llama antes de enviar código opcional al LLM.

### 0.3 Nuevas migraciones de BD

Un archivo Alembic por grupo:

**Grupo A — Modificar tablas existentes:**
- `test_cases`: renombrar `name → title`; agregar `description`; hacer `expected_result` no nulo; agregar `suggestion (bool)`, `style_findings (JSONB)`, `variant_id (FK→data_variants)`, `rule_id (FK→rules)`; marcar `preconditions`, `steps`, `boundary` como obsoletos (NULL permitido temporalmente).
- `certifications`: agregar `service (varchar)`, `business_summary (text)`.
- `assignments`: renombrar `row_ref → affiliate_ref`; agregar `validation_date (date)`, `explanation (text)`.

**Grupo B — Tablas nuevas (paso 1):**
- `rules`: `certification_id`, `code`, `operation`, `returns`, `conditions`, `source (JSONB)`, `from_code (bool)`.
- `test_case_revisions`: `test_case_id`, `previous (JSONB)`, `reason (edit/refocus)`, `created_by`.

**Grupo C — Tablas nuevas (pasos 3-4):**
- `format_fields`: `certification_id`, `key`, `value`, `source (deduced/analyst)`, `confirmed`.
- `analyst_defaults`: `user_id`, `key`, `value`.
- `data_variants`: `certification_id`, `code`, `description_nl`, `quantity (JSONB)`, `conditions (JSONB)`, `validation_date (JSONB)`, `mutates_state`, `confirmed`.
- `data_requests` (extender existente): agregar `kind (initial/complementary)`, `fields (JSONB)`, `sent_at`, `grouping_note (text nullable)`.
- `field_catalogs`: `module`, `service`, `key`, `label`, `data_type`, `synonyms (JSONB)`.

**Grupo D — Tablas nuevas (pasos 5-9):**
- `risk_rules`: `service`, `code`, `description`, `definition (JSONB)`, `effect (exclude/penalize)`, `weight`, `is_active`.
- `discarded_candidates`: `certification_id`, `variant_id`, `affiliate_ref`, `reasons (JSONB)`.
- `soap_templates`: `service`, `operation`, `sample_xml (text)`, `variables (JSONB)`, `assertions (JSONB)`, `owner_id`, `is_global`.
- `soap_requests`: `test_case_id`, `template_id`, `xml (text)`, `generated_at`.
- `soap_responses`: `test_case_id`, `file_path`, `extracted (JSONB)`, `comparison (JSONB)`, `uploaded_at`.
- `evidence_texts`: `test_case_id`, `condition (text)`, `query (text)`, `result (text)`, `observations (text)`.
- `review_findings`: `certification_id`, `code`, `severity`, `message`, `target (JSONB)`, `accepted`, `comment`.

**Criterio de aceptación fase 0:** `alembic upgrade head` sin errores; tests existentes siguen pasando; la etapa `context` sigue siendo la inicial de nuevas certificaciones.

---

## Fase 1 — Pasos 1, 2 y 3 (contexto, casos y formato)

RF-10 a RF-33.

### 1.1 Paso 1 — Entender el requerimiento (cambios en `context/`)

**Agregar:**
- `context/models.py`: tabla `rules`.
- `context/domain/rules_extractor.py`: prompt LLM para extraer reglas estructuradas `{code, operation, returns, conditions, source}`. Recibe el contexto enmascarado por PIIGuard.
- `context/service.py`: método `extract_rules(certification_id) → list[Rule]`. Llama al LLM con el contexto combinado de las fuentes y almacena las reglas.
- `context/tasks.py`: tarea Celery que orquesta resumen + reglas + ambigüedades en una sola llamada (o en pasos secuenciales con el mismo contexto).

**Modificar:**
- `context/service.py`: añadir `generate_business_summary()` que produce un párrafo corto en lenguaje de negocio y lo guarda en `certifications.business_summary`.
- `context/domain/ambiguity_rules.py`: agregar tipo `undefined_tiebreak` (ej. "qué pasa si la fecha coincide exactamente con el límite").
- Retirar referencias a `acceptance_criteria` — las reglas las reemplazan.
- Soporte para `source_code` como cuarta fuente de contexto: pasa por `SecretsScanner` antes del LLM.

**Nuevos endpoints:**
```
GET /certifications/{id}/rules
PATCH /rules/{id}
POST /certifications/{id}/context/code   (nueva fuente)
```

**Tests unitarios:**
- `test_rules_extractor.py`: FakeProvider devuelve reglas estructuradas; verificar que el código no va al LLM sin pasar por SecretsScanner.
- `test_ambiguity_rules.py`: agregar caso `undefined_tiebreak`.
- `test_secrets_scanner.py`: detectar cadena de conexión y token en texto de código.

### 1.2 Paso 2 — Casos en formato corto (cambios en `testcases/`)

**Cambios de modelo:**
- `test_cases`: `title` (era `name`), `description` (nuevo), `suggestion (bool)`.
- Nueva tabla `test_case_revisions` para el historial de reenfoque.

**Linter → Style:**
- Renombrar `testcases/domain/linter.py` → `testcases/domain/style.py`.
- Reemplazar reglas L01–L09 por S01–S06 (ver §6.4 del SPEC):
  - S01: título ≤ 120 caracteres.
  - S02: descripción ≤ 2 oraciones.
  - S03: sin palabras vagas.
  - S04: un solo resultado esperado.
  - S05: terminología consistente con el glosario.
  - S06: toda regla tiene al menos un caso (aviso a nivel de certificación).
- Los avisos son `warning`, no bloquean.

**Reenfocar (RF-24):**
- `testcases/service.py`: método `refocus_case(case_id, new_objective)` que llama al LLM con el objetivo nuevo; el LLM reescribe título, descripción, resultado esperado y propone nueva variante; guarda revisión en `test_case_revisions`.
- Tarea Celery: `tasks.refocus_case`.
- Endpoint: `POST /testcases/{id}/refocus`.

**Casos de bug (RF-22):**
- El generador de casos (`testcases/tasks.py`) limita la propuesta a **un caso por escenario** para bugs. Las sugerencias extra se marcan con `suggestion=true` y se excluyen de la propuesta por defecto.

**Tests:**
- `test_style.py`: S01–S06 con casos válidos e inválidos.
- `test_refocus.py`: FakeProvider simula reescritura; verificar que `test_case_revisions` se crea.
- `test_bug_single_case.py`: con descripción de bug de un escenario, solo se genera un caso no-sugerencia.

### 1.3 Paso 3 — Llenar el CO-FR-VRA-03 (nuevo módulo `certformat/`)

**Estructura:**
```
certformat/
  router.py
  schemas.py
  models.py      # FormatField, AnalystDefault
  service.py
  repository.py
  domain/
    deducer.py   # lógica de deducción de campos del contexto
```

**`certformat/domain/deducer.py`:**
- Función `deduce_fields(context_sources, cert) → dict[str, FieldValue]`:
  - `requirement_id`: del `external_code` de la certificación.
  - `change_name`: del título.
  - `client`, `application`, `module`: del contexto o módulo registrado.
  - `description`: del `business_summary`.
- Cada campo retorna `{value, source: "deduced", confirmed: False}`.

**`certformat/service.py`:**
- `deduce_fields(certification_id)`: llama al deducer y persiste en `format_fields`.
- `save_analyst_fields(certification_id, values)`: guarda los campos que aporta el analista y actualiza `analyst_defaults` para ese usuario.
- `get_fields(certification_id)`: devuelve todos los campos con su origen y estado de confirmación.

**Endpoints:**
```
GET  /certifications/{id}/format-fields
PUT  /certifications/{id}/format-fields
```

**Configuración:** `templates/co-fr-vra-03/fields.yaml` (ver §6.11 del SPEC). El deducer lee este YAML para saber qué campos existen, su `source` por defecto y su celda.

**Tests:**
- `test_deducer.py`: con una certificación sintética, los 6 campos deducibles tienen el valor correcto.
- Verificar que los campos del analista guardan el valor sugerido para la próxima vez.

**Criterio de aceptación fase 1:** con el fixture de brecha sintética, se genera el resumen de negocio, las reglas con su fuente, se detecta el desempate no definido. Los casos usan formato corto, las sugerencias extras no entran por defecto. El reenfoque actualiza el caso y crea una revisión. El formato muestra los 6 campos deducidos y pide los 5 restantes con valor sugerido.

---

## Fase 2 — Pasos 4 y 5 (solicitud de datos y asignación)

RF-40 a RF-59.

### 2.1 Paso 4 — Solicitud de datos (nuevo módulo `datarequest/`)

**Estructura:**
```
datarequest/
  router.py
  schemas.py
  models.py      # DataVariant, DataRequest, FieldCatalog
  service.py
  repository.py
  tasks.py
  domain/
    variant_builder.py   # NL → DSL estructurado (con LLM)
    request_template.py  # rellena data_request.md.j2
```

**`datarequest/domain/variant_builder.py`:**
- Toma un caso aprobado con su regla y produce una `DataVariant` con:
  - `description_nl`: descripción en palabras (LLM).
  - `quantity`: cantidad de titulares/beneficiarios necesarios.
  - `conditions`: condiciones estructuradas del afiliado (DSL existente de `filter.py`).
  - `validation_date`: estrategia (`offset`, `fixed` o `derived`).
- El LLM propone la versión estructurada; el analista la confirma.
- Si el servicio requiere varias filas por afiliado, `variant_builder` lo indica en `grouping_note` (texto natural); no asume estructura jerárquica por defecto.

**`datarequest/domain/request_template.py`:**
- Usa `templates/data_request.md.j2` con Jinja2.
- Agrupa las variantes por condición similar (RF-40).
- Opcionalmente pasa el texto por el LLM para pulo de redacción (validar que no cambia cantidades ni campos).

**`FieldCatalog`:**
- Tabla `field_catalogs`: catálogo por módulo/servicio. Los campos no tienen nivel fijo; el catálogo crece con cada certificación.
- `datarequest/service.py`: `suggest_fields(certification_id)` propone los campos del catálogo correspondiente al servicio/módulo.
- Cuando el analista agrega un campo nuevo, ofrece guardarlo en el catálogo (RF-44).

**Endpoints:**
```
GET/PUT  /certifications/{id}/variants
POST     /certifications/{id}/data-requests
GET/PATCH /data-requests/{id}
GET/POST  /field-catalogs
```

**Nuevo template:** `templates/data_request.md.j2`.

**Tests:**
- `test_variant_builder.py`: FakeProvider produce variante estructurada; verificar tipos de campo y estrategia de fecha.
- `test_request_template.py`: con 2 variantes sintéticas, el texto generado contiene la condición en palabras, la cantidad y todos los campos del catálogo. Sin SQL en el texto.
- `test_field_catalog.py`: agregar campo nuevo persiste en el catálogo.

### 2.2 Paso 5 — Asignación (cambios en `testdata/`)

**Cambios en `testdata/domain/`:**

**`testdata/domain/loader.py` (nuevo o reescrito):**
- Carga el archivo de fábrica (Excel o txt) y aplica el mapeo de columnas confirmado.
- Si la variante indica `grouping_note` (varias filas por afiliado), agrupa por la clave configurada antes de filtrar. Por defecto no asume agrupación.
- Devuelve un `DataFrame` de afiliados (una fila por afiliado) listo para el filtro.

**`testdata/domain/filter.py` (sin cambios de interfaz):**
- El DSL de condiciones existente ya soporta todos los casos de afiliado plano.
- Si en el futuro un servicio requiere condiciones sobre filas agrupadas, se extiende el DSL con una función `aggregate` genérica; no se anticipa ahora.

**`testdata/domain/risk_rules.py` (nuevo):**
- `RiskRule` dataclass: `code`, `description`, `definition (dict)`, `effect (exclude|penalize)`, `weight`.
- `evaluate_risks(affiliate_row, validation_date, rules) → list[RiskResult]`: aplica cada regla sobre la fila del afiliado.
- Reglas iniciales K05–K06; las adicionales (específicas del servicio) vienen de la BD como combinación de condiciones del DSL.
- **K05:** campos de la condición con valor nulo.
- **K06:** el afiliado se usó en certificaciones recientes (consulta a BD).

**`testdata/domain/dates.py` (ampliar):**
- Estrategias: `offset` (días calendario o hábiles desde un campo base), `fixed` (valor literal), `derived` (expresión calculada localmente).
- Validar que la fecha resultante cae dentro de cualquier rango de vigencia que aplique (configurable).

**`testdata/domain/assignment.py` (reescribir):**
- Recibe `affiliates_df`, `variants`, `col_map`, `risk_rules`.
- Por variante: filtrar candidatos → evaluar riesgos → calcular fecha de validación → construir matriz de costo → `linear_sum_assignment`.
- Guardar `discarded_candidates` con motivo por cada afiliado excluido.
- Construir `explanation` en lenguaje natural con plantilla local (sin LLM).
- Retorna `CaseAssignment` con `affiliate_ref`, `validation_date`, `explanation`, `alternate_rows`.

**Nuevos endpoints:**
```
POST /certifications/{id}/assign
GET  /certifications/{id}/discarded
GET/POST /risk-rules
PATCH /risk-rules/{id}
```

**Tests:**
- `test_loader.py`: archivo plano y archivo con varias filas por afiliado (agrupación activada) → DataFrame correcto en ambos casos.
- `test_risk_rules.py`: K05 y K06 con afiliados sintéticos; verificar exclusión y motivo.
- `test_assignment_v2.py`: fixture de 300 afiliados; verificar usuario distinto por caso, fecha válida, lista de descartados y determinismo (misma entrada = misma salida).
- `test_no_pii_reaches_llm.py`: ampliar para incluir archivo de fábrica.

**Criterio de aceptación fase 2:** la solicitud generada contiene condición en palabras, cantidad por rol y campos del catálogo; sin SQL. Con el archivo sintético, K05 descarta afiliados con datos faltantes, cada caso tiene usuario distinto con fecha válida y explicación. Misma entrada = misma salida.

---

## Fase 3 — Pasos 6, 7, 8 y 9 (ejecución, análisis, documentación y revisión)

RF-60 a RF-103.

### 3.1 Paso 6 — Módulo SOAP (nuevo `soap/`)

**Estructura:**
```
soap/
  router.py
  schemas.py
  models.py      # SoapTemplate, SoapRequest
  service.py
  repository.py
  tasks.py
  domain/
    template_builder.py  # detecta variables en XML de ejemplo
    request_generator.py # llena plantilla con lxml
    soapui_exporter.py   # genera proyecto SoapUI XML
    wsdl_parser.py       # (opcional) importa operaciones desde WSDL
```

**`soap/domain/template_builder.py`:**
- Recibe un XML de ejemplo de SoapUI.
- Detecta candidatos a variables: números de documento, fechas, tipos de documento (regex + heurística).
- Devuelve lista de variables candidatas con su XPath y valor de ejemplo.
- El analista confirma cuáles son variables y cuál es su fuente (`affiliate_field`, `validation_date`, `fixed`).

**`soap/domain/request_generator.py`:**
- Usa `lxml` para llenar la plantilla.
- Sustituye las variables con los valores del afiliado asignado y la fecha de validación.
- Valida que el resultado es XML bien formado.
- Si hay WSDL, valida contra el esquema.

**`soap/domain/soapui_exporter.py`:**
- Genera un proyecto SoapUI `.xml` con un test case por CP.

**Endpoints:**
```
GET/POST /soap-templates
POST /soap-templates/detect-variables
PATCH /soap-templates/{id}
POST /certifications/{id}/soap-requests/generate
GET  /certifications/{id}/soap-requests/export   (SoapUI XML)
```

**Tests:**
- `test_template_builder.py`: XML de ejemplo → variables detectadas correctamente.
- `test_request_generator.py`: template + afiliado sintético → XML válido con los valores correctos.
- `test_soapui_exporter.py`: fixture de 3 casos → proyecto SoapUI con 3 test cases.
- Verificar que las plantillas no guardan valores de credenciales ni endpoints con contraseña.

### 3.2 Paso 7 — Análisis de respuesta (nuevo `analysis/`)

**Estructura:**
```
analysis/
  router.py
  schemas.py
  models.py      # SoapResponse, Execution (extender)
  service.py
  repository.py
  tasks.py
  domain/
    response_parser.py   # lxml, XPath, detección de SOAP Fault
    comparator.py        # comparación determinística valor a valor
    classifier.py        # passed / failed / data_limitation
```

**`analysis/domain/response_parser.py`:**
- Parsea el XML de respuesta con `lxml`.
- Extrae los valores de las XPath configuradas en `SoapTemplate.assertions`.
- Detecta SOAP Faults y mensajes de error.
- No envía nada al LLM (el XML puede contener datos del afiliado).

**`analysis/domain/comparator.py`:**
- Compara valor por valor: XPath esperada (calculada localmente de la regla + datos del afiliado) vs. obtenida de la respuesta.
- Devuelve `{field, expected, obtained, match}` por aserción.

**`analysis/domain/classifier.py`:**
- `passed`: todas las aserciones coinciden.
- `failed`: alguna no coincide y los datos del afiliado eran válidos.
- `data_limitation`: la respuesta revela un tramo o riesgo no detectado antes.
- El LLM redacta la observación recibiendo **solo** el resultado de la comparación (campo, match/no-match, códigos no personales), nunca la respuesta ni datos del afiliado.

**Endpoints:**
```
POST /testcases/{id}/response
PUT  /testcases/{id}/execution
```

**Tests:**
- `test_response_parser.py`: 4 respuestas sintéticas (correcta, valor distinto, SOAP Fault, tramo no presente).
- `test_comparator.py`: comparación valor a valor con los 4 casos.
- `test_classifier.py`: `passed`, `failed`, `failed`, `data_limitation` respectivamente.
- Verificar que el texto enviado al LLM para la observación no contiene datos del afiliado ni la respuesta SOAP.

### 3.3 Paso 8 — Documentación (cambios en `deliverables/`)

**Nuevos subdominios:**
- `deliverables/domain/evidence_texts.py`:
  - `generate_evidence_text(case, assignment, soap_request, soap_response) → EvidenceText`.
  - Genera localmente (con plantilla Jinja2): condición, consulta, resultado y observaciones.
  - Sin LLM (puede contener datos del afiliado en los campos calculados).

**Adaptar `excel_filler.py`:**
- Usar el nuevo `fields.yaml` con `source` por campo.
- Llenar también los textos de evidencia por caso en la hoja correspondiente.
- Bloque de evidencia: condición, consulta, resultado, observaciones, pantallazos.

**Nuevos endpoints:**
```
POST  /certifications/{id}/evidence-texts/generate
PATCH /evidence-texts/{id}
```

**Tests:**
- `test_evidence_texts.py`: con fixture sintético, los 4 campos de texto se generan correctamente.
- `test_excel_filler_v2.py`: la plantilla ficticia se llena con `fields.yaml` y los textos de evidencia sin alterar estilos.

### 3.4 Paso 9 — Revisión final (nuevo `review/`)

**Estructura:**
```
review/
  router.py
  schemas.py
  models.py      # ReviewFinding
  service.py
  repository.py
  domain/
    checks.py    # C01–C09
```

**`review/domain/checks.py`:**
- Función `run_checks(certification_id, ...) → list[ReviewFinding]`.
- Controles C01–C09 (ver §6.13 del SPEC):
  - C01: caso `passed` sin observación → warning.
  - C02: campo del formato vacío → error.
  - C03: fechas con formato incorrecto o incoherentes → error.
  - C04: códigos de caso no consecutivos o duplicados → warning.
  - C05: nombre del requerimiento o código distinto entre formato, casos, nota y correo → error.
  - C06: caso sin pantallazo o con evidencia rechazada → error.
  - C07: caso sin clasificación final → error.
  - C08: caso `data_limitation` sin justificación → warning.
  - C09: texto de evidencia vacío → error.
- Cada hallazgo tiene `severity`, `message` y `target` (enlace a la etapa donde se corrige).

**Endpoints:**
```
POST /certifications/{id}/review
GET  /certifications/{id}/review
PATCH /review-findings/{id}   # aceptar warning con comentario
```

**Lógica de entrega:** bloquear la descarga del zip si hay findings de severidad `error` sin aceptar.

**Tests:**
- `test_checks.py`: fixture con cada error sembrado → detectado con severidad correcta.
- `test_delivery_blocked.py`: no se puede descargar el zip con un C02 activo.

**Criterio de aceptación fase 3:**
- Plantilla SOAP creada desde request de ejemplo, con variables; requests generados son XML válido.
- 4 respuestas sintéticas → `passed`, `failed`, `failed`, `data_limitation`.
- Textos de evidencia generados; formato sin alterar la plantilla; zip descargable.
- La revisión detecta los errores sembrados y bloquea la entrega hasta corregirlos.

---

## Fase 4 — Mapa Vivo (Neo4j)

RF-110 a RF-113. Sin cambios respecto a v1.1 salvo que los nodos ahora incluyen `rules`, `variants`, y `risk_rules` aprendidas.

**Cambios principales:**
- Al cerrar una certificación, registrar en el grafo: módulo, servicio, reglas, variantes, reglas de riesgo descubiertas (`data_limitation`), casos y resultados.
- Sugerir para nuevas certificaciones del mismo servicio: variantes conocidas, campos del catálogo usados antes, reglas de riesgo activas.

---

## Fase 5 — Piloto de equipo

- Permisos de líder: ver certificaciones y métricas de todo el equipo.
- Plantillas, catálogos de campos y reglas de riesgo globales (disponibles para todos, no solo por analista).
- Ajustes de usabilidad basados en uso real.

---

## Fase 6 — Tablero de métricas

RF-103 completo:
- Nuevas métricas de v2.0: casos propuestos vs. conservados, % reenfocados, % con `data_limitation`, casos reemplazados manualmente, precisión de la propuesta (% conservados).
- Comparación contra línea base.
- Exportación a Excel.

---

## Orden de commits recomendado

Cada commit cita `RF-XX` y lleva tests:

```
feat(certifications): 10-stage flow for v2.0   RF-02
feat(llm): secrets scanner for optional code   RF-16
feat(core): migrations group A (test_cases, certifications, assignments)
feat(core): migrations group B (rules, test_case_revisions)
feat(context): extract rules from context      RF-14
feat(context): business summary generation     RF-13
feat(context): undefined_tiebreak ambiguity    RF-15
feat(testcases): format corto title+desc+result RF-20
feat(testcases): style checks S01-S06          RF-26
feat(testcases): refocus with LLM              RF-24
feat(certformat): field deduction and saving   RF-30 RF-31
feat(core): migrations group C (format_fields, variants, data_requests, field_catalogs)
feat(datarequest): variant builder             RF-41 RF-43
feat(datarequest): data request template       RF-41 RF-43
feat(core): migrations group D (risk_rules, discarded, soap, analysis, review)
feat(testdata): segment grouping from file     RF-52
feat(testdata): aggregate conditions DSL       RF-53
feat(testdata): risk rules K01-K06             RF-54
feat(testdata): validation date strategies     RF-55
feat(testdata): assignment v2 with explanation RF-55 RF-56 RF-57
feat(soap): template builder from SoapUI       RF-60
feat(soap): request generator with lxml        RF-61
feat(soap): SoapUI project export              RF-62
feat(analysis): response parser XPath          RF-70
feat(analysis): deterministic comparator       RF-71
feat(analysis): classifier passed/failed/data_limitation RF-72
feat(deliverables): evidence texts generation  RF-80
feat(deliverables): excel filler v2 fields.yaml RF-81
feat(review): checks C01-C09                   RF-90
feat(review): delivery gate on errors          RF-91
```

---

## Qué NO cambiar (para no romper lo que funciona)

- `core/security.py` — no tocar.
- `core/db.py`, `core/config.py` — no tocar.
- `llm/provider.py`, `llm/pii_guard.py` — no tocar (solo agregar `secrets_scanner.py`).
- `testdata/domain/filter.py` — solo ampliar con agregados; el DSL básico no cambia.
- `testdata/domain/dates.py` — solo agregar estrategias nuevas.
- `evidence/domain/ocr.py` — no tocar.
- Tests existentes — todos deben seguir pasando. Si un test rompe con la migración, el problema es la migración, no el test.

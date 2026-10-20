# Copiloto de Certificación QA — Beyond Health

## Qué es este proyecto

Herramienta web que acompaña al analista QA en la certificación de bugs y brechas de Beyond Health (sistema de salud desarrollado por Sonda), de punta a punta: entiende lo que se certifica, propone casos, llena el formato CO-FR-VRA-03, redacta la solicitud de datos a fábrica, escoge los usuarios de prueba, genera los requests REST/JSON o SOAP/XML, analiza las respuestas, redacta las evidencias y revisa todo antes de entregar.

**Principio rector: el sistema propone y el analista decide.** Casos definitivos, usuarios usados y clasificación final de cada resultado son decisión del analista.

El sistema funciona **aparte de la red privada de Sonda**: trabaja con lo que el analista carga y devuelve textos y archivos. No se conecta a Beyond Health, a los servicios REST/SOAP, a la base de datos de fábrica, a TFS ni a Aranda.

**La especificación técnica completa está en `docs/SPEC.md` (v2.1).** Léela antes de planear cualquier fase. Cita los identificadores `RF-XX` en commits y tests. Ante dudas de detalle manda `docs/SPEC.md`, salvo las reglas de seguridad de aquí, que siempre prevalecen.

## Reglas de seguridad (obligatorias)

- Los datos de afiliados son datos de salud (Ley 1581 de 2012). **Nunca** se envían al LLM datos de afiliados: archivo de fábrica, respuestas de servicios (REST ni SOAP), pantallazos ni texto OCR.
- Filtrado, reglas de riesgo, asignación, cálculo de fechas, OCR, NER de nombres y comparación de respuestas son **locales y determinísticos**. Nunca los decide el LLM.
- Al LLM solo llegan: texto del contexto (documento, descripción, reporte y código opcional) enmascarado por `PIIGuard`, variantes en palabras, nombres de columnas y resultados de comparación sin datos personales.
- **PIIGuard aplica dos capas antes de enviar cualquier texto al LLM:** (1) regex de documentos, correos y teléfonos; (2) NER local con spaCy `es_core_news_md` para detectar nombres propios de personas. **Los nombres nunca van al LLM para ser detectados.**
- La misma detección NER se aplica al anonimizar entradas para la biblioteca interna de certificaciones.
- El código fuente opcional pasa por el escáner de secretos antes del LLM.
- Las plantillas de request no guardan credenciales ni endpoints con contraseña.
- Durante el desarrollo se usan **solo datos sintéticos** en `fixtures/`. Nunca subir al repositorio documentos, archivos de fábrica, respuestas o pantallazos reales.
- Secretos solo en variables de entorno (`.env`, excluido de git).
- `.gitignore` debe excluir `data/`, `uploads/`, `.env`, `*.xlsx` fuera de `fixtures/` y `templates/`.

## Flujo adaptable por receta

Las etapas posibles son: `context` → `testcases` → `format` → `data_request` → `assignment` → `execution` → `analysis` → `documentation` → `review` → `closed`.

**Cada certificación activa solo las etapas que define su receta.** Un bug con un solo caso por pantalla va de contexto a caso, ejecución, evidencia y nota TFS. Un servicio SOAP/XML usa las diez etapas. El flujo de 10 etapas es el máximo, no el camino obligatorio.

La receta se copia a `active_stages` al crear la certificación. El analista puede agregar o quitar etapas; cada cambio queda registrado. Hay 8 recetas iniciales:

| Receta | Etapas que activa |
|---|---|
| `bug_simple` | context, testcases, format, execution, documentation, review |
| `bug_before_after` | context, testcases, format, execution, documentation, review |
| `bug_negative_control` | context, testcases, format, execution, documentation, review |
| `brecha_date_rule` | context, testcases, format, execution, documentation, review (+ data_request y assignment opcionales) |
| `service_soap_xml` | todas las etapas (required) |
| `service_rest_json` | context, testcases, format, execution, analysis, documentation, review (+ data_request y assignment opcionales; ambas pasan a required si data_origin = factory_request) |
| `file_batch` | context, testcases, format, execution, documentation, review |
| `client_cases` | context, testcases, format, execution, documentation, review |

## Reglas de casos de prueba

- El estilo de redacción lo define la receta y se puede cambiar por caso: `short`, `validate_that`, `action_validations`, `consult_service`, `full_sheet`.
- **Bugs: un caso por escenario.** Si el bug tiene un solo escenario, un solo caso. No agregar casos de regresión ni de frontera extra si el analista no los pide.
- En brechas, los casos extra (frontera, variantes adicionales) se muestran como **sugerencia** y no entran por defecto.
- Sin palabras vagas ("correctamente", "adecuadamente"), un solo resultado esperado observable, terminología consistente.
- Los avisos de redacción no bloquean. El linter adapta sus reglas al estilo elegido.

## Datos de prueba

- Variante de datos = condición en palabras + versión estructurada (condiciones del afiliado, estrategia de fecha de validación). La estructura concreta depende del servicio.
- Algunos archivos de fábrica traen varias filas por afiliado (ej. registros hijos o tramos). Si es así, se indica en `grouping_note` y se agrupa antes de filtrar. No asumir esta estructura por defecto.
- El analista puede validar un usuario candidato individualmente para **cualquier origen de datos** (incluido `manual_search`): ingresa la vigencia y los registros hijos, y el sistema evalúa los riesgos y propone la fecha de validación (RF-50b).
- Los pasos 4 y 5 (solicitud a fábrica y asignación masiva) se activan solo cuando `data_origin = factory_request` o el analista los agrega explícitamente.
- Reglas de riesgo generales: K05 (datos incompletos) y K06 (uso reciente). Adicionales configurables por servicio sin código: K01–K04 están implementadas y sembradas para `servicio_regimen`.
- Asignación: un usuario distinto por caso, hasta 2 suplentes, explicación en lenguaje natural y lista de descartados con motivo. Misma entrada, misma salida (determinístico).

## Clasificaciones de resultado

`passed` | `failed` | `inconclusive` | `blocked` | `new_defect`

- `inconclusive` requiere una sub-razón de la tabla `inconclusive_reasons` (editable por el líder): `data_condition_not_met`, `date_out_of_validity`, `data_already_corrected`, `other_validation_noise`, `other`.
- `blocked` significa que no fue posible ejecutar el caso (ambiente, acceso, proceso fallido). No eliminar del código.
- `new_defect`: se ofrece generar un `factory_message` pre-rellenado. La referencia TFS/Aranda se exige antes de entregar (control C12), no al clasificar.
- `data_limitation` **no es clasificación**; usar `inconclusive` con la sub-razón `data_condition_not_met`.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 (async) + Alembic, Pydantic v2, Celery + Redis.
- **Datos y documentos:** pandas, openpyxl, python-docx, pdfplumber, scipy, holidays, lxml (SOAP/XML y XPath), jsonpath-ng (REST/JSON y JSONPath), Jinja2.
- **OCR:** Tesseract vía pytesseract.
- **NER local:** spaCy 3 + `es_core_news_md`. Detección de nombres propios: local, nunca en el LLM.
- **LibreOffice headless:** conversión de `.doc` binario (opcional).
- **Base de datos:** PostgreSQL 16. Neo4j 5 solo en la fase del Mapa Vivo.
- **Frontend:** Next.js (App Router) + TypeScript + Tailwind + shadcn/ui.
- **Despliegue:** Docker Compose en una VM.

## Arquitectura

Monolito modular; cada módulo con `router`, `schemas`, `models`, `service`, `repository`, `tasks` y `domain/` (lógica pura, la más testeada).

```
backend/app/
  core/          # config, seguridad, logging, BD, almacenamiento, auditoría
  llm/           # LLMProvider intercambiable, PIIGuard (regex + NER spaCy), escáner de secretos, prompts versionados
  users/  certifications/
  recipes/       # recetas, estilos de caso, patrones de caso, sub-razones de inconclusive
  library/       # biblioteca de certificaciones (anonimización + búsqueda FTS)
  context/       # paso 1
  testcases/     # paso 2
  certformat/    # paso 3
  datarequest/   # paso 4
  testdata/      # paso 5
  requests/      # paso 6: plantillas y generación REST/JSON + SOAP/XML (renombrado de soap/)
  evidence/      # paso 6: pantallazos y OCR
  analysis/      # paso 7
  deliverables/  # paso 8
  review/        # paso 9
  metrics/
  knowledge/     # Mapa Vivo — fase 5
```

**Capa de LLM intercambiable:** la política de IA externa no está definida. Toda llamada pasa por `LLMProvider` (Anthropic, Ollama o Fake), elegido por variable de entorno. Ningún módulo importa un SDK de IA directamente.

**Multiusuario desde el diseño:** el piloto lo usa un solo analista, pero el modelo incluye usuarios, roles y certificaciones por analista.

## Dominio

- **Certificación:** validar un bug corregido o una brecha (cambio funcional). Casi una por día.
- **Bugs no tienen documento de requerimiento.** Nunca asumir que existe uno.
- **Normalmente no hay acceso al código.** Nunca asumir que existe.
- **Fábrica:** equipo que entrega los datos de prueba a partir de la solicitud en palabras.
- **CO-FR-VRA-03:** formato oficial de pruebas. Se llena una plantilla base; el formato nunca se altera.
- Algunos servicios manejan registros hijos o tramos (varias filas por afiliado). La estructura varía por servicio; el sistema la descubre a través del catálogo de campos y el mapeo confirmado por el analista.

## Convenciones

- Código y nombres técnicos en inglés; interfaz y documentos generados en español.
- Tests con `pytest`; todo módulo nuevo lleva tests con fixtures sintéticos.
- Trabajar por fases: planear antes de implementar y no adelantar fases futuras sin pedirlo.
- Lo propuesto por el sistema se distingue siempre de lo confirmado por el analista.
- Citar `RF-XX` en commits y tests.

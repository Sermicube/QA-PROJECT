# Copiloto de Certificación QA — Beyond Health

## Qué es este proyecto

Herramienta web que acompaña al analista QA en el ciclo de certificación de Beyond Health (sistema de salud desarrollado por Sonda). Recibe el documento de requerimiento y una base de usuarios de prueba; detecta ambigüedades, redacta casos de prueba claros, asigna automáticamente usuarios de prueba a cada caso y genera los entregables (formato CO-FR-VRA-03, nota TFS, correo de certificación). Cada certificación alimenta un grafo de conocimiento del sistema ("Mapa Vivo").

El sistema funciona **aparte de la red privada de Sonda**: trabaja con archivos que el analista sube y devuelve archivos. No se conecta a Beyond Health, TFS ni Aranda en el MVP.

**La especificación técnica completa está en `docs/SPEC.md`.** Léela antes de planear cualquier fase. Cita los identificadores `RF-XX` en commits y tests. Este archivo es el resumen; ante dudas de detalle, manda `docs/SPEC.md` (salvo las reglas de seguridad de aquí, que siempre prevalecen).

## Reglas de seguridad (obligatorias)

- Los datos de afiliados son datos de salud (Ley 1581 de 2012). **Nunca** se envían datos de afiliados (cédulas, nombres, contratos, fechas personales) a un modelo de IA.
- El filtrado y la asignación de usuarios de prueba son **locales y determinísticos** (pandas/SQL), nunca decididos por el LLM.
- Al LLM solo llegan: texto de requerimientos, condiciones de los casos y nombres de columnas.
- Durante el desarrollo se usan **solo datos sintéticos** en `fixtures/`. Nunca subir al repositorio documentos o bases reales.
- Secretos (API keys) solo en variables de entorno (`.env`, excluido de git). Nunca en el código.
- `.gitignore` debe excluir `data/`, `uploads/`, `.env`, `*.xlsx` fuera de `fixtures/` y `templates/`.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 (async) + Alembic, Pydantic v2.
- **Base de datos:** PostgreSQL 16. Neo4j 5 se agrega en la fase del Mapa Vivo (no antes).
- **Tareas pesadas:** Celery + Redis (OCR, generación de documentos, llamadas al LLM).
- **Frontend:** Next.js (App Router) + TypeScript + Tailwind.
- **Documentos:** `python-docx` y `pdfplumber` (lectura de requerimientos), `openpyxl` (plantilla CO-FR-VRA-03), `pandas` (bases de usuarios en Excel/txt).
- **OCR:** Tesseract vía `pytesseract` (validar hora del sistema y URL en pantallazos).
- **Despliegue:** Docker Compose, pensado para correr en una VM.

## Arquitectura

Monolito modular. Carpetas del backend:

```
backend/app/
  core/          # config, seguridad, logging, sesión de BD
  llm/           # capa de proveedor intercambiable
  requirements/  # Módulo 1: análisis de requerimiento y ambigüedades
  testcases/     # Módulo 1: redacción de casos con plantilla estricta
  testdata/      # Módulo 2: carga de bases, mapeo de columnas, asignación
  evidence/      # Módulo 2: pantallazos + validación OCR
  deliverables/  # CO-FR-VRA-03, nota TFS, correo de certificación
  knowledge/     # Mapa Vivo (Neo4j) — fase posterior
  metrics/       # registro de tiempos y métricas por etapa
```

### Capa de LLM intercambiable

La política de uso de IA externa aún no está definida. Toda llamada al modelo pasa por una interfaz `LLMProvider` con implementaciones para API externa (Anthropic) y modelo local (Ollama). El proveedor se elige por variable de entorno. Ningún módulo importa un SDK de IA directamente.

### Multiusuario desde el diseño

El piloto lo usa un solo analista, pero el modelo de datos incluye desde el inicio usuarios, roles (analista, líder) y certificaciones asociadas a un analista.

## Dominio

- **Certificación:** proceso de validar un bug corregido o una "Brecha" (cambio funcional). Casi una por día.
- **Tipos:** bug (viene de Aranda, se registra en TFS) y brecha (viene de un documento de requerimiento).
- **Documento de requerimiento:** casi siempre en el mismo formato (tipo "Modelo Análisis Producto Solicitud de Cambio").
- **Módulo piloto:** Novedades de afiliación (exclusión de beneficiario, terminación de contrato, cambio de fecha inicio IPS).
- **Base de usuarios:** Excel o txt (a veces delimitado por `|`). Las columnas **varían según el caso**, por eso existe el mapeo de columnas.
- **Evidencia:** cada pantallazo debe mostrar la **hora del sistema y la URL**.
- **CO-FR-VRA-03:** formato oficial de Pruebas de Calidad de Software. Se guarda como plantilla base con campos marcados; el sistema **solo llena campos**, nunca altera el formato.

## Reglas de redacción de casos de prueba

- Nombre: `Validar que el sistema [acción] cuando [una sola condición]`.
- Estructura: nombre, precondiciones, datos, pasos, resultado esperado (uno solo, observable, idealmente con el mensaje exacto del sistema).
- Una condición por caso.
- Prohibidas palabras vagas: "correctamente", "adecuadamente", "de forma exitosa".
- Terminología consistente (ej. siempre "fecha de efecto").
- Si hay una comparación de fechas o montos, sugerir los casos de frontera: anterior, igual y posterior.
- Paso a paso breve, en el estilo: "Se accede a Beyond Health, al apartado de ... y se genera la novedad ... con fecha ...".

## Detector de ambigüedades

Marcar en el requerimiento:
- Comparaciones sin frontera definida ("mayor", "anterior", "hasta", "a partir de") sin aclarar el caso igual.
- Unidades implícitas ("días" sin decir hábiles o calendario).
- Ramas faltantes (qué pasa si la condición no se cumple).
- Contradicciones entre secciones del documento.

Salida: lista de preguntas. La interpretación acordada queda registrada en la certificación.

## Asignación de usuarios de prueba

1. Cada caso se traduce a condiciones estructuradas (JSON), con ayuda del LLM y confirmación del analista.
2. El LLM propone el mapeo columna → campo del dominio; el analista confirma. Los mapeos confirmados se guardan y se reutilizan.
3. Filtrado determinístico local.
4. Asignación: un usuario distinto por caso (las pruebas modifican el estado del afiliado), más suplentes. Priorizar usuarios que cumplen con menos condiciones extra.
5. Explicar por qué cada usuario cumple. Si ningún usuario cumple, generar una solicitud precisa de datos.
6. Calcular la fecha a digitar cuando aplique (considerar festivos colombianos para días hábiles).

## Métricas

Registrar por certificación: tiempo por etapa, tiempo buscando datos, % de casos con datos asignados automáticamente, ambigüedades detectadas, casos devueltos por redacción y evidencias rechazadas por OCR.

## Hoja de ruta

1. Mes 1: preparación, línea base de métricas.
2. Meses 2–3: Módulo 1 (requerimiento, ambigüedades, casos).
3. Meses 4–5: Módulo 2 (bases, mapeo, asignación, plantilla, OCR).
4. Mes 6: entregables automáticos + piloto individual.
5. Meses 7–8: Mapa Vivo (Neo4j) + sugerencia de regresión + segundo módulo.
6. Mes 9: piloto con 2–3 analistas.
7. Mes 10: tablero de métricas y presentación.

## Convenciones

- Código y nombres técnicos en inglés; textos de interfaz y documentos generados en español.
- Tests con `pytest`; todo módulo nuevo lleva tests con fixtures sintéticos.
- Trabajar por fases: planear antes de implementar y no adelantar fases futuras sin pedirlo.

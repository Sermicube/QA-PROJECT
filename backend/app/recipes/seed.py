"""Seed data for recipes, case_styles, case_patterns and inconclusive_reasons.

Called once at startup by service.seed_all() — idempotent (upsert by code).
"""

from typing import Any

# Stage mode constants
R = "required"
O = "optional"
N = "not_applicable"

ALL_STAGES = [
    "context", "testcases", "format", "data_request",
    "assignment", "execution", "analysis", "documentation", "review", "closed",
]


def _bug_stages() -> dict[str, str]:
    return {
        "context": R, "testcases": R, "format": R,
        "data_request": N, "assignment": N,
        "execution": R, "analysis": N,
        "documentation": R, "review": R, "closed": R,
    }


RECIPES: list[dict[str, Any]] = [
    {
        "code": "bug_simple",
        "name": "Bug — un caso",
        "description": "Bug con un único escenario de prueba.",
        "stages": _bug_stages(),
        "default_case_style": "short",
        "default_evidence_style": "default",
        "default_execution_channel": "ui",
        "default_data_origin": "developer_case",
        "suggested_case_pattern": "one_case",
        "is_builtin": True,
    },
    {
        "code": "bug_before_after",
        "name": "Bug — antes/después",
        "description": "Bug que se demuestra comparando el comportamiento antes y después de la corrección.",
        "stages": _bug_stages(),
        "default_case_style": "short",
        "default_evidence_style": "before_after",
        "default_execution_channel": "ui",
        "default_data_origin": "developer_case",
        "suggested_case_pattern": "before_after",
        "is_builtin": True,
    },
    {
        "code": "bug_negative_control",
        "name": "Bug — negativo + control",
        "description": "Reproduce el bug y verifica que el comportamiento válido del sistema sigue funcionando.",
        "stages": _bug_stages(),
        "default_case_style": "short",
        "default_evidence_style": "default",
        "default_execution_channel": "ui",
        "default_data_origin": "colleague_request",
        "suggested_case_pattern": "negative_control",
        "is_builtin": True,
    },
    {
        "code": "brecha_date_rule",
        "name": "Brecha con regla de fecha",
        "description": "Brecha funcional cuya validación gira en torno a una comparación de fechas.",
        "stages": {
            "context": R, "testcases": R, "format": R,
            "data_request": O, "assignment": O,
            "execution": R, "analysis": N,
            "documentation": R, "review": R, "closed": R,
        },
        "default_case_style": "validate_that",
        "default_evidence_style": "default",
        "default_execution_channel": "ui",
        "default_data_origin": "colleague_request",
        "suggested_case_pattern": "boundary",
        "is_builtin": True,
    },
    {
        "code": "service_soap_xml",
        "name": "Servicio SOAP/XML",
        "description": "Certificación de un servicio SOAP/XML. Usa todas las etapas: solicitud a fábrica, asignación de usuarios, ejecución, análisis, documentación, revisión y cierre.",
        "stages": {s: R for s in ALL_STAGES},
        "default_case_style": "consult_service",
        "default_evidence_style": "service_blocks",
        "default_execution_channel": "soap_xml",
        "default_data_origin": "factory_request",
        "suggested_case_pattern": "matrix_by_role",
        "is_builtin": True,
    },
    {
        "code": "service_rest_json",
        "name": "Servicio REST/JSON",
        "description": "Certificación de un servicio REST con análisis por JSONPath. "
                       "Solicitud a fábrica y asignación de usuarios son opcionales; "
                       "se activan si el origen de datos es 'Solicitud a fábrica'.",
        "stages": {
            "context": R, "testcases": R, "format": R,
            "data_request": O, "assignment": O,
            "execution": R, "analysis": R,
            "documentation": R, "review": R, "closed": R,
        },
        "default_case_style": "consult_service",
        "default_evidence_style": "service_blocks",
        "default_execution_channel": "rest_json",
        "default_data_origin": "manual_search",
        "suggested_case_pattern": "matrix_by_role",
        "is_builtin": True,
    },
    {
        "code": "file_batch",
        "name": "Cargue de archivo o batch",
        "description": "Proceso de cargue masivo de archivo o ejecución de proceso por lotes.",
        "stages": _bug_stages(),
        "default_case_style": "action_validations",
        "default_evidence_style": "default",
        "default_execution_channel": "file_upload",
        "default_data_origin": "client_file",
        "suggested_case_pattern": "one_case",
        "is_builtin": True,
    },
    {
        "code": "client_cases",
        "name": "Casos del cliente",
        "description": "El cliente entrega su propio plan de pruebas. El analista lo importa y ejecuta.",
        "stages": _bug_stages(),
        "default_case_style": "validate_that",
        "default_evidence_style": "default",
        "default_execution_channel": "ui",
        "default_data_origin": "client_file",
        "suggested_case_pattern": "client_cases",
        "is_builtin": True,
    },
]


CASE_STYLES: list[dict[str, Any]] = [
    {
        "code": "short",
        "name": "Formato corto",
        "fields": {"title": "required", "description": "required", "expected_result": "required"},
        "template_jinja": "{{ title }}\n{{ description }}\nResultado esperado: {{ expected_result }}",
        "lint_rules": {"max_title_chars": 120, "max_description_sentences": 2, "single_expected_result": True},
        "example": "Semanas de cotización — antes/después\nSe replica la prueba del desarrollador...\nResultado esperado: El sistema muestra 4 semanas.",
    },
    {
        "code": "validate_that",
        "name": "Validar que…",
        "fields": {"title": "required", "description": "required", "expected_result": "required"},
        "template_jinja": "Validar que {{ system }} {{ action }} cuando {{ condition }}.\nResultado esperado: {{ expected_result }}",
        "lint_rules": {"must_start_with_validar_que": True, "single_expected_result": True},
        "example": "Validar que el sistema rechace el cargue PILA cuando el tipo de cotizante no está habilitado para el período liquidado.\nResultado esperado: El sistema muestra el mensaje de error E-043 y descarta el registro.",
    },
    {
        "code": "action_validations",
        "name": "Al [acción], se ejecutan las siguientes validaciones",
        "fields": {"title": "required", "action": "required", "validations": "required", "expected_result": "required"},
        "template_jinja": "Al {{ action }}, se ejecutan las siguientes validaciones:\n{% for v in validations %}- {{ v }}\n{% endfor %}Resultado esperado: {{ expected_result }}",
        "lint_rules": {"allows_multiple_expected_results": True},
        "example": "Al radicar una incapacidad con fecha de inicio posterior a la fecha de egreso del empleador:\nSe ejecutan las siguientes validaciones:\n– El sistema valida que la fecha de inicio no supere la fecha de egreso.\nResultado esperado: El sistema rechaza la radicación y muestra el mensaje I-011.",
    },
    {
        "code": "consult_service",
        "name": "Consultar un…",
        "fields": {"title": "required", "role": "required", "query_type": "optional", "condition": "required", "expected_result": "required"},
        "template_jinja": "Consultar un {{ role }} por {{ query_type }}, donde {{ condition }}.\nResultado esperado: {{ expected_result }}",
        "lint_rules": {"single_expected_result": True},
        "example": "Consultar un cobro por tipo de consulta 1, donde el empleador tiene aportes pendientes en el período liquidado.\nResultado esperado: El servicio devuelve la lista de cobros con estado = 'PENDIENTE' para ese empleador.",
    },
    {
        "code": "full_sheet",
        "name": "Hoja completa de la plantilla",
        "fields": {
            "title": "required",
            "objective": "required",
            "preconditions": "required",
            "input_data": "required",
            "steps": "required",
            "expected_result": "required",
        },
        "template_jinja": "Objetivo: {{ objective }}\nPrecondiciones: {{ preconditions }}\nDatos de entrada: {{ input_data }}\nActividades y pasos:\n{% for s in steps %}{{ loop.index }}. {{ s }}\n{% endfor %}Resultado esperado: {{ expected_result }}",
        "lint_rules": {"requires_preconditions": True, "no_title_char_limit": True},
        "example": "Objetivo: Verificar que el cargue masivo PILA rechace registros con tipo de documento PC...",
    },
]


CASE_PATTERNS: list[dict[str, Any]] = [
    {"code": "one_case", "name": "Un solo caso", "description": "Un único escenario de prueba.", "n_cases_typical": "1", "notes": ""},
    {"code": "before_after", "name": "Antes y después", "description": "Replica la prueba del desarrollador y muestra el cambio.", "n_cases_typical": "2", "notes": ""},
    {"code": "negative_control", "name": "Negativo + control", "description": "Reproduce el bug y verifica que lo válido funciona.", "n_cases_typical": "2", "notes": ""},
    {"code": "boundary", "name": "Frontera", "description": "Antes / igual / después del límite de la regla.", "n_cases_typical": "3", "notes": ""},
    {"code": "threshold_control_oos", "name": "Umbral + control + fuera de alcance", "description": "Límite numérico, control y caso fuera del alcance del cambio.", "n_cases_typical": "3-5", "notes": ""},
    {"code": "by_scenario", "name": "Por escenario de negocio", "description": "Un caso por escenario diferenciado.", "n_cases_typical": "2-4", "notes": ""},
    {"code": "matrix_by_role", "name": "Matriz por rol", "description": "N roles × M condiciones.", "n_cases_typical": "6-12", "notes": "Los roles dependen del módulo certificado (ej. titular/beneficiario en afiliaciones, empleador/trabajador en incapacidades)."},
    {"code": "client_cases", "name": "Casos del cliente", "description": "Importar plan existente del cliente.", "n_cases_typical": "variable", "notes": ""},
    {"code": "logic_monitoring", "name": "Lógica + monitoreo/log", "description": "Un caso para la lógica y otro para el log o monitoreo.", "n_cases_typical": "2", "notes": "Disponible como alternativa en file_batch."},
]


INCONCLUSIVE_REASONS: list[dict[str, Any]] = [
    {
        "code": "data_condition_not_met",
        "label": "El dato no cumplía realmente la condición de la variante",
        "description": "El usuario de prueba seleccionado no satisfacía la condición de la variante al momento de la ejecución.",
    },
    {
        "code": "date_out_of_validity",
        "label": "La fecha de validación cae fuera de la vigencia del registro",
        "description": "La fecha usada no está dentro del período de vigencia del registro de prueba.",
    },
    {
        "code": "data_already_corrected",
        "label": "El registro ya había sido corregido manualmente en BD",
        "description": "El dato que debía reproducir el escenario fue corregido directamente en base de datos antes de la ejecución.",
    },
    {
        "code": "other_validation_noise",
        "label": "El resultado se debe a otra validación del sistema (ruido)",
        "description": "El sistema devolvió un resultado distinto al esperado por una validación ajena a la regla certificada.",
    },
    {
        "code": "other",
        "label": "Otro motivo",
        "description": "Motivo distinto a los anteriores. Documentar en la observación del caso.",
    },
]

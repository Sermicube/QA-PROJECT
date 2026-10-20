from dataclasses import dataclass, field

from pydantic import BaseModel

from app.llm.provider import Message

# Mock arrays returned when the system prompt matches specific task types
_CRITERIA_RESPONSE = """
[
  {"code": "CA-01", "text": "El sistema debe validar que la fecha de efecto no sea retroactiva más de 6 meses.", "source_kind": "analyst_description", "source_section": null},
  {"code": "CA-02", "text": "Cuando la fecha es inválida, el sistema debe rechazar la operación y mostrar un mensaje de error.", "source_kind": "analyst_description", "source_section": null}
]
""".strip()

_AMBIGUITIES_RESPONSE = """
[
  {
    "type": "undefined_result",
    "fragment": "el sistema rechaza la solicitud",
    "location": "analyst_description › Descripción",
    "explanation": "No se especifica qué mensaje exacto muestra el sistema al rechazar.",
    "question": "¿Cuál es el mensaje exacto (código y texto) que el sistema debe mostrar cuando rechaza la solicitud?"
  },
  {
    "type": "missing_branch",
    "fragment": "cuando la fecha de efecto es válida el sistema permite la novedad",
    "location": "analyst_description › Descripción",
    "explanation": "Solo se describe el caso en que la fecha es válida, pero no qué ocurre cuando no lo es.",
    "question": "¿Qué debe hacer el sistema exactamente cuando la fecha es inválida?"
  },
  {
    "type": "incomplete_context",
    "fragment": "módulo de exclusiones",
    "location": "analyst_description › Descripción",
    "explanation": "No se indica la pantalla ni la ruta de navegación exacta dentro del módulo.",
    "question": "¿Cuál es la pantalla y ruta exacta dentro de Beyond Health donde se registra la exclusión?"
  },
  {
    "type": "implicit_assumption",
    "fragment": "el servicio retorna los datos del afiliado",
    "location": "analyst_description › Descripción",
    "explanation": "El contexto asume que el servicio retorna siempre los mismos datos que se enviaron, pero no está verificado que el identificador retornado coincida con el enviado.",
    "question": "¿El servicio garantiza que el identificador retornado es el mismo que se envió en la solicitud?"
  }
]
""".strip()

_CASES_RESPONSE = """
[
  {
    "code": "CP-01",
    "name": "Validar que el sistema rechace la exclusión cuando la fecha de efecto supera el límite retroactivo",
    "criteria_ids": ["CA-01"],
    "preconditions": ["El analista tiene acceso a Beyond Health", "Existe un afiliado activo en el sistema"],
    "steps": ["Se accede a Beyond Health, al módulo de Exclusiones y se intenta registrar una exclusión con fecha de efecto de hace 7 meses"],
    "expected_result": "El sistema muestra el mensaje de error E-042 y no registra la exclusión",
    "boundary": "after",
    "flags": {
      "pending_assumption": false,
      "assumption_note": null,
      "is_suggestion": false,
      "requires_db_verification": false
    }
  },
  {
    "code": "CP-02",
    "name": "Validar que el sistema permita la exclusión cuando la fecha de efecto está dentro del límite",
    "criteria_ids": ["CA-01"],
    "preconditions": ["El analista tiene acceso a Beyond Health", "Existe un afiliado activo en el sistema"],
    "steps": ["Se accede a Beyond Health, al módulo de Exclusiones y se registra una exclusión con fecha de efecto de hace 3 meses"],
    "expected_result": "El sistema registra la exclusión y muestra confirmación",
    "boundary": "before",
    "flags": {
      "pending_assumption": false,
      "assumption_note": null,
      "is_suggestion": false,
      "requires_db_verification": false
    }
  }
]
""".strip()

_SUMMARY_RESPONSE = """
{
  "business_summary": "La certificación valida que el sistema Beyond Health controle las restricciones temporales al registrar exclusiones de afiliados, rechazando retroactividades superiores a 6 meses.",
  "rules": [
    "No se permiten exclusiones con fecha de efecto anterior a 6 meses desde la fecha actual.",
    "Cuando la fecha es inválida el sistema debe mostrar el código de error E-042.",
    "La validación aplica a todos los tipos de novedad que registran fecha de efecto."
  ]
}
""".strip()


@dataclass
class LLMCall:
    system: str
    messages: list[Message]
    schema_name: str | None = None

    def all_text(self) -> str:
        parts = [self.system, *(m.content for m in self.messages)]
        return "\n".join(parts)


class FakeProvider:
    """Proveedor de LLM falso para tests. Actúa como espía.

    Si `response` no se especifica, devuelve respuestas apropiadas según el
    tipo de tarea deducido del system prompt (por el nombre del archivo de prompt).
    Esto permite que los tests de integración y E2E reciban datos con formato correcto.
    """

    def __init__(self, response: str | None = None) -> None:
        self._fixed_response = response
        self.calls: list[LLMCall] = []

    @property
    def all_sent_text(self) -> str:
        return "\n".join(c.all_text() for c in self.calls)

    def reset(self) -> None:
        self.calls.clear()

    def _pick_response(self, system: str) -> str:
        if self._fixed_response is not None:
            return self._fixed_response
        sys_low = system.lower()
        if "extract_criteria" in sys_low or "criterios de aceptación" in sys_low:
            return _CRITERIA_RESPONSE
        if "detect_ambiguities" in sys_low or "ambigüedades semánticas" in sys_low:
            return _AMBIGUITIES_RESPONSE
        if "generate_cases" in sys_low or "caso_style" in sys_low or ("reglas de redacción" in sys_low and "casos de prueba" in sys_low):
            return _CASES_RESPONSE
        if "extract_summary" in sys_low or "resumen de negocio" in sys_low:
            return _SUMMARY_RESPONSE
        return "{}"

    async def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
    ) -> str:
        self.calls.append(LLMCall(system=system, messages=messages))
        return self._pick_response(system)

    async def structured(
        self,
        system: str,
        messages: list[Message],
        schema: type[BaseModel],
        *,
        max_tokens: int = 1024,
    ) -> BaseModel:
        self.calls.append(LLMCall(system=system, messages=messages, schema_name=schema.__name__))
        response = self._fixed_response if self._fixed_response is not None else "{}"
        return schema.model_validate_json(response)

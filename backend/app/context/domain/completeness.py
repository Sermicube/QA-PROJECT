"""Asistente de completitud para la descripción del analista (RF-10d).

Solo aplica a fuentes de tipo 'analyst_description'.
Los hallazgos son sugerencias, no bloquean el flujo.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CompletenessFinding:
    field: str
    message: str


_MIN_LENGTH = 30  # mínimo de caracteres para considerar un campo no vacío


def _filled(value: object) -> bool:
    return bool(value) and len(str(value).strip()) >= _MIN_LENGTH


def check_bug_description(content: dict) -> list[CompletenessFinding]:
    """Revisa los campos de una descripción guiada de tipo bug."""
    findings: list[CompletenessFinding] = []

    if not _filled(content.get("bug_behavior")):
        findings.append(CompletenessFinding(
            field="bug_behavior",
            message="No se describió el comportamiento reportado del bug. "
                    "Indicar qué ocurría antes de la corrección ayuda a definir el caso de no regresión.",
        ))
    if not _filled(content.get("what_to_test")):
        findings.append(CompletenessFinding(
            field="what_to_test",
            message="No se indicó qué se va a probar. Este campo es obligatorio para generar los casos.",
        ))
    if not _filled(content.get("expected_result")):
        findings.append(CompletenessFinding(
            field="expected_result",
            message="No se indicó el resultado esperado tras la corrección. "
                    "Sin este dato, el caso de prueba no puede tener un criterio de éxito claro.",
        ))
    if not content.get("fix") and not _filled(content.get("fix")):
        findings.append(CompletenessFinding(
            field="fix",
            message="No se describió la corrección aplicada. "
                    "Conocerla ayuda a diseñar casos que validen la solución específica.",
        ))

    return findings


def check_brecha_description(content: dict) -> list[CompletenessFinding]:
    """Revisa los campos de una descripción guiada de tipo brecha."""
    findings: list[CompletenessFinding] = []

    if not _filled(content.get("what_changes")):
        findings.append(CompletenessFinding(
            field="what_changes",
            message="No se describió qué cambia en el sistema. "
                    "Esta información define el alcance de los casos de prueba.",
        ))
    if not _filled(content.get("what_to_test")):
        findings.append(CompletenessFinding(
            field="what_to_test",
            message="No se indicó qué se va a probar. Este campo es obligatorio para generar los casos.",
        ))
    if not _filled(content.get("expected_result")):
        findings.append(CompletenessFinding(
            field="expected_result",
            message="No se indicó el resultado esperado. "
                    "Sin este dato, no es posible definir criterios de aceptación.",
        ))

    return findings


def check_free_text(text: str) -> list[CompletenessFinding]:
    """Revisa una descripción de texto libre (modo no guiado)."""
    findings: list[CompletenessFinding] = []
    if len(text.strip()) < _MIN_LENGTH:
        findings.append(CompletenessFinding(
            field="free_text",
            message="La descripción es muy corta. Agregar más detalle mejorará la calidad de los casos generados.",
        ))
    return findings


def check_description(cert_type: str, content: dict) -> list[CompletenessFinding]:
    """Punto de entrada principal. cert_type: 'bug' | 'brecha'."""
    free_text: str = content.get("free_text") or ""
    if free_text:
        return check_free_text(free_text)
    if cert_type == "bug":
        return check_bug_description(content)
    return check_brecha_description(content)

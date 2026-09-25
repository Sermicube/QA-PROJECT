"""Generación de pasos con datos asignados (RF-30)."""
from __future__ import annotations

import re


def generate_steps(
    test_case: dict,
    assignment: dict,
    derived_values: dict,
) -> list[str]:
    """Rellena los pasos del caso con los datos asignados.

    Sustituye placeholders {campo} con valores reales.
    Si no hay placeholders, añade una nota con los datos al final.
    """
    all_values = {**assignment, **derived_values}
    steps: list[str] = list(test_case.get("steps") or [])
    filled: list[str] = []
    any_substituted = False

    for step in steps:
        new_step = step
        for key, val in all_values.items():
            placeholder = f"{{{key}}}"
            if placeholder in new_step:
                new_step = new_step.replace(placeholder, str(val))
                any_substituted = True
        filled.append(new_step)

    if not any_substituted and all_values:
        data_note = "Datos a utilizar: " + ", ".join(
            f"{k}={v}" for k, v in all_values.items() if v is not None
        )
        filled.append(data_note)

    return filled

"""Linter de redacción de casos de prueba (RF-17, §6.4).

Reglas L01–L08. Cada regla devuelve una lista de LintIssue.
La función `lint_case` aplica todas las reglas a un solo caso.
La función `lint_batch` aplica además L07 y L08, que necesitan contexto.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LintIssue:
    code: str        # L01 … L08
    message: str
    severity: str = "error"  # error | warning


@dataclass
class CaseInput:
    """Datos del caso que el linter necesita."""
    code: str
    name: str
    preconditions: list[str]
    steps: list[str]
    expected_result: str
    boundary: Optional[str] = None          # before | equal | after
    criteria_ids: list[str] = field(default_factory=list)


# Palabras vagas prohibidas (L03)
_VAGUE = re.compile(
    r"\b(correctamente|adecuadamente|de\s+forma\s+exitosa|de\s+manera\s+correcta|"
    r"exitosamente|satisfactoriamente|bien|sin\s+problemas|sin\s+errores)\b",
    re.IGNORECASE,
)

# Detecta "cuando X y Y" — dos condiciones en el nombre (L02)
_DOUBLE_CONDITION = re.compile(
    r"\bcuando\b.+?\by\b.+?\bcuando\b|\bcuando\b.+?\by\s+(?:el|la|los|las|se|no)\b",
    re.IGNORECASE,
)

# Comparadores que sugieren necesidad de frontera (L07)
_COMPARATORS = re.compile(
    r"\b(mayor|menor|anterior|posterior|superior|inferior|antes\s+de|después\s+de|"
    r"a\s+partir\s+de|hasta|desde)\b",
    re.IGNORECASE,
)


# ────────────────────────────────────────────────────────────────────────────
# Reglas individuales
# ────────────────────────────────────────────────────────────────────────────

def _l01(case: CaseInput) -> list[LintIssue]:
    if not case.name.lower().startswith("validar que el sistema"):
        return [LintIssue("L01", 'El nombre debe empezar con "Validar que el sistema …"')]
    return []


def _l02(case: CaseInput) -> list[LintIssue]:
    name = case.name
    when_count = len(re.findall(r"\bcuando\b", name, re.IGNORECASE))
    if when_count == 0:
        return [LintIssue("L02", 'El nombre debe contener exactamente una condición iniciada con "cuando"')]
    if when_count > 1:
        return [LintIssue("L02", "El nombre contiene más de una condición. Separar en casos distintos.")]
    if _DOUBLE_CONDITION.search(name):
        return [LintIssue("L02", 'El nombre une dos condiciones con "y". Separar en casos distintos.')]
    return []


def _l03(case: CaseInput) -> list[LintIssue]:
    issues: list[LintIssue] = []
    for part, label in [
        (case.name, "nombre"),
        (case.expected_result, "resultado esperado"),
        (" ".join(case.steps), "pasos"),
    ]:
        m = _VAGUE.search(part)
        if m:
            issues.append(LintIssue(
                "L03", f'Palabra vaga "{m.group()}" en {label}. Usar un criterio observable concreto.'
            ))
    return issues


def _l04(case: CaseInput) -> list[LintIssue]:
    # Heurística: más de una oración en expected_result sugiere más de un resultado
    sentences = re.split(r"[.;]\s+", case.expected_result.strip())
    non_empty = [s for s in sentences if s.strip()]
    if len(non_empty) > 2:
        return [LintIssue(
            "L04",
            "El resultado esperado parece contener más de un resultado. Describir solo el resultado principal observable.",
            severity="warning",
        )]
    return []


def _l06(case: CaseInput) -> list[LintIssue]:
    if len(case.name) > 200:
        return [LintIssue("L06", f"El nombre tiene {len(case.name)} caracteres; el máximo es 200.")]
    return []


def lint_case(case: CaseInput) -> list[LintIssue]:
    """Aplica L01-L04 y L06 (no necesitan contexto de otros casos)."""
    issues: list[LintIssue] = []
    for rule in (_l01, _l02, _l03, _l04, _l06):
        issues.extend(rule(case))
    return issues


# ────────────────────────────────────────────────────────────────────────────
# Reglas que necesitan el lote completo
# ────────────────────────────────────────────────────────────────────────────

def _l07(cases: list[CaseInput]) -> dict[str, list[LintIssue]]:
    """L07: si hay comparación, verificar que existen los 3 casos de frontera."""
    results: dict[str, list[LintIssue]] = {c.code: [] for c in cases}

    # Agrupar por "nombre base" (quitando la parte de frontera)
    boundaries_present: dict[str, set[str]] = {}
    for case in cases:
        if _COMPARATORS.search(case.name) and case.boundary:
            base = _strip_boundary_suffix(case.name)
            boundaries_present.setdefault(base, set()).add(case.boundary)

    for case in cases:
        if _COMPARATORS.search(case.name):
            if not case.boundary:
                results[case.code].append(LintIssue(
                    "L07",
                    "El caso contiene una comparación pero no tiene campo 'boundary' definido. "
                    "Indicar si este caso corresponde a la condición anterior, igual o posterior.",
                    severity="warning",
                ))
            else:
                base = _strip_boundary_suffix(case.name)
                present = boundaries_present.get(base, set())
                missing = {"before", "equal", "after"} - present
                if missing:
                    results[case.code].append(LintIssue(
                        "L07",
                        f"Faltan casos de frontera para esta comparación: {', '.join(sorted(missing))}. "
                        "Agregar un caso para cada valor de frontera (anterior, igual, posterior).",
                        severity="warning",
                    ))
    return results


def _l08(cases: list[CaseInput], criterion_ids: list[str]) -> dict[str, list[LintIssue]]:
    """L08: todo criterio debe tener al menos un caso que lo referencie."""
    results: dict[str, list[LintIssue]] = {c.code: [] for c in cases}
    covered = {cid for c in cases for cid in c.criteria_ids}
    uncovered = set(criterion_ids) - covered
    if uncovered and cases:
        # Añadir la advertencia al primer caso
        results[cases[0].code].append(LintIssue(
            "L08",
            f"Los siguientes criterios no tienen caso de prueba: {', '.join(sorted(uncovered))}.",
            severity="warning",
        ))
    return results


def _l09(cases: list[CaseInput], glossary: list[dict]) -> dict[str, list[LintIssue]]:
    """L09 (RF-63): detecta términos del glosario usados con nombre incorrecto.

    glossary: lista de {name, synonyms} aportada por KnowledgeService.
    Solo actúa si el glosario tiene al menos un término.
    """
    results: dict[str, list[LintIssue]] = {c.code: [] for c in cases}
    if not glossary:
        return results

    for entry in glossary:
        canonical = entry.get("name", "").lower().strip()
        synonyms_raw: list[str] = entry.get("synonyms", []) or []
        synonyms = [s.lower().strip() for s in synonyms_raw if s.strip()]
        if not canonical or not synonyms:
            continue

        # Si algún sinónimo aparece en el caso pero el nombre canónico no, marcar
        for case in cases:
            full_text = (
                case.name + " " + " ".join(case.steps) + " " + case.expected_result
            ).lower()
            for syn in synonyms:
                if re.search(r"\b" + re.escape(syn) + r"\b", full_text):
                    if not re.search(r"\b" + re.escape(canonical) + r"\b", full_text):
                        results[case.code].append(LintIssue(
                            "L09",
                            f'Se usa "{syn}" pero el término canónico del glosario es "{entry["name"]}". '
                            "Usar terminología consistente.",
                            severity="warning",
                        ))
                        break  # un aviso por término por caso es suficiente
    return results


def lint_batch(
    cases: list[CaseInput],
    criterion_ids: list[str] | None = None,
    glossary: list[dict] | None = None,
) -> dict[str, list[LintIssue]]:
    """Aplica todas las reglas al lote completo. Devuelve {case_code: [issues]}."""
    results: dict[str, list[LintIssue]] = {}
    for case in cases:
        results[case.code] = lint_case(case)

    l07 = _l07(cases)
    l08 = _l08(cases, criterion_ids or [])
    l09 = _l09(cases, glossary or [])
    for code in results:
        results[code].extend(l07.get(code, []))
        results[code].extend(l08.get(code, []))
        results[code].extend(l09.get(code, []))

    return results


def _strip_boundary_suffix(name: str) -> str:
    """Quita la parte de frontera del nombre para agrupar casos relacionados."""
    suffixes = [
        r"\s+cuando\s+(?:la\s+)?fecha.*?(?:anterior|igual|posterior).*$",
        r"\s+cuando\s+(?:el\s+)?valor.*?(?:anterior|igual|posterior|mayor|menor).*$",
    ]
    for pat in suffixes:
        name = re.sub(pat, "", name, flags=re.IGNORECASE)
    return name.strip()

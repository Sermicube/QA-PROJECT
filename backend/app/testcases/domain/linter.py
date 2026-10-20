"""Linter de redacción de casos de prueba (RF-17, §6.4).

Reglas S01–S08. Todos los avisos son de severidad "warning" — no bloquean aprobación.
La función `lint_case` aplica S01-S05 a un solo caso.
La función `lint_batch` aplica además S06-S08, que necesitan contexto de lote.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LintIssue:
    code: str        # S01 … S08
    message: str
    severity: str = "warning"  # siempre "warning" — los avisos de estilo no bloquean


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


# Palabras vagas prohibidas (S03)
_VAGUE = re.compile(
    r"\b(correctamente|adecuadamente|de\s+forma\s+exitosa|de\s+manera\s+correcta|"
    r"exitosamente|satisfactoriamente|bien|sin\s+problemas|sin\s+errores|"
    r"correcto|correcta|correctos|correctas)\b",
    re.IGNORECASE,
)

# Detecta "cuando X y Y" — dos condiciones en el nombre (S02)
_DOUBLE_CONDITION = re.compile(
    r"\bcuando\b.+?\by\b.+?\bcuando\b|\bcuando\b.+?\by\s+(?:el|la|los|las|se|no)\b",
    re.IGNORECASE,
)

# Comparadores que sugieren necesidad de frontera (S06)
_COMPARATORS = re.compile(
    r"\b(mayor|menor|anterior|posterior|superior|inferior|antes\s+de|después\s+de|"
    r"a\s+partir\s+de|hasta|desde)\b",
    re.IGNORECASE,
)


# ────────────────────────────────────────────────────────────────────────────
# Reglas individuales
# ────────────────────────────────────────────────────────────────────────────

def _detect_style(name: str) -> str:
    """Infer case style from name pattern."""
    return "consult_service" if name.lower().startswith("consultar ") else "validate_that"


def _s01(case: CaseInput) -> list[LintIssue]:
    style = _detect_style(case.name)
    if style == "consult_service":
        # Accept "Consultar [noun(s)] por/donde [...]" — singular or plural
        pattern = re.compile(r"^consultar\s+\w", re.IGNORECASE)
        if not pattern.match(case.name):
            return [LintIssue("S01", 'El nombre debería empezar con "Consultar [entidad] por [tipo], donde [condición]"')]
        return []
    if not case.name.lower().startswith("validar que el sistema"):
        return [LintIssue("S01", 'El nombre debería empezar con "Validar que el sistema …"')]
    return []


def _s02(case: CaseInput) -> list[LintIssue]:
    style = _detect_style(case.name)
    if style == "consult_service":
        return []
    name = case.name
    when_count = len(re.findall(r"\bcuando\b", name, re.IGNORECASE))
    if when_count == 0:
        return [LintIssue("S02", 'El nombre debería contener una condición iniciada con "cuando"')]
    if when_count > 1:
        return [LintIssue("S02", "El nombre contiene más de una condición. Considera separar en casos distintos.")]
    if _DOUBLE_CONDITION.search(name):
        return [LintIssue("S02", 'El nombre une dos condiciones con "y". Considera separar en casos distintos.')]
    return []


def _s03(case: CaseInput) -> list[LintIssue]:
    issues: list[LintIssue] = []
    for part, label in [
        (case.name, "nombre"),
        (case.expected_result, "resultado esperado"),
        (" ".join(case.steps), "pasos"),
    ]:
        m = _VAGUE.search(part)
        if m:
            issues.append(LintIssue(
                "S03", f'Palabra vaga "{m.group()}" en {label}. Usar un criterio observable concreto.'
            ))
    return issues


def _s04(case: CaseInput) -> list[LintIssue]:
    sentences = re.split(r"[.;]\s+", case.expected_result.strip())
    non_empty = [s for s in sentences if s.strip()]
    if len(non_empty) > 2:
        return [LintIssue(
            "S04",
            "El resultado esperado parece contener más de un resultado. Describir solo el resultado principal observable.",
        )]
    return []


def _s05(case: CaseInput) -> list[LintIssue]:
    if len(case.name) > 200:
        return [LintIssue("S05", f"El nombre tiene {len(case.name)} caracteres; el máximo recomendado es 200.")]
    return []


def lint_case(case: CaseInput) -> list[LintIssue]:
    """Aplica S01-S05 (no necesitan contexto de otros casos)."""
    issues: list[LintIssue] = []
    for rule in (_s01, _s02, _s03, _s04, _s05):
        issues.extend(rule(case))
    return issues


# ────────────────────────────────────────────────────────────────────────────
# Reglas que necesitan el lote completo
# ────────────────────────────────────────────────────────────────────────────

def _s06(cases: list[CaseInput]) -> dict[str, list[LintIssue]]:
    """S06: si hay comparación, verificar que existen los 3 casos de frontera."""
    results: dict[str, list[LintIssue]] = {c.code: [] for c in cases}

    boundaries_present: dict[str, set[str]] = {}
    for case in cases:
        if _COMPARATORS.search(case.name) and case.boundary:
            base = _strip_boundary_suffix(case.name)
            boundaries_present.setdefault(base, set()).add(case.boundary)

    for case in cases:
        if _COMPARATORS.search(case.name):
            if not case.boundary:
                results[case.code].append(LintIssue(
                    "S06",
                    "El caso contiene una comparación pero no tiene campo 'boundary' definido. "
                    "Indicar si corresponde a la condición anterior, igual o posterior.",
                ))
            else:
                base = _strip_boundary_suffix(case.name)
                present = boundaries_present.get(base, set())
                missing = {"before", "equal", "after"} - present
                if missing:
                    results[case.code].append(LintIssue(
                        "S06",
                        f"Faltan casos de frontera para esta comparación: {', '.join(sorted(missing))}. "
                        "Considerar agregar un caso para cada valor de frontera.",
                    ))
    return results


def _s07(cases: list[CaseInput], criterion_ids: list[str]) -> dict[str, list[LintIssue]]:
    """S07: todo criterio debería tener al menos un caso que lo referencie."""
    results: dict[str, list[LintIssue]] = {c.code: [] for c in cases}
    covered = {cid for c in cases for cid in c.criteria_ids}
    uncovered = set(criterion_ids) - covered
    if uncovered and cases:
        results[cases[0].code].append(LintIssue(
            "S07",
            f"Los siguientes criterios no tienen caso de prueba: {', '.join(sorted(uncovered))}.",
        ))
    return results


def _s08(cases: list[CaseInput], glossary: list[dict]) -> dict[str, list[LintIssue]]:
    """S08 (RF-63): detecta términos del glosario usados con nombre incorrecto."""
    results: dict[str, list[LintIssue]] = {c.code: [] for c in cases}
    if not glossary:
        return results

    for entry in glossary:
        canonical = entry.get("name", "").lower().strip()
        synonyms_raw: list[str] = entry.get("synonyms", []) or []
        synonyms = [s.lower().strip() for s in synonyms_raw if s.strip()]
        if not canonical or not synonyms:
            continue

        for case in cases:
            full_text = (
                case.name + " " + " ".join(case.steps) + " " + case.expected_result
            ).lower()
            for syn in synonyms:
                if re.search(r"\b" + re.escape(syn) + r"\b", full_text):
                    if not re.search(r"\b" + re.escape(canonical) + r"\b", full_text):
                        results[case.code].append(LintIssue(
                            "S08",
                            f'Se usa "{syn}" pero el término canónico del glosario es "{entry["name"]}". '
                            "Usar terminología consistente.",
                        ))
                        break
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

    s06 = _s06(cases)
    s07 = _s07(cases, criterion_ids or [])
    s08 = _s08(cases, glossary or [])
    for code in results:
        results[code].extend(s06.get(code, []))
        results[code].extend(s07.get(code, []))
        results[code].extend(s08.get(code, []))

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

"""Tests de la regla L09 del linter — terminología del glosario (RF-63)."""
from app.testcases.domain.linter import CaseInput, lint_batch


def _case(name: str, expected: str = "El sistema muestra el resultado.") -> CaseInput:
    return CaseInput(
        code="CP-01",
        name=name,
        preconditions=[],
        steps=["Se accede al sistema"],
        expected_result=expected,
    )


GLOSSARY = [
    {"name": "exclusión", "definition": "Exclusión de beneficiario", "synonyms": ["desvinculación", "baja"]},
    {"name": "fecha de efecto", "definition": "Fecha de inicio del efecto", "synonyms": ["fecha efectiva"]},
]


def test_linter_l09_inconsistent_term():
    case = _case("Validar que el sistema procese la desvinculación cuando el contrato expira")
    results = lint_batch([case], glossary=GLOSSARY)
    codes = [i.code for i in results["CP-01"]]
    assert "L09" in codes


def test_linter_l09_no_issue_when_glossary_empty():
    case = _case("Validar que el sistema procese la desvinculación cuando el contrato expira")
    results = lint_batch([case], glossary=[])
    codes = [i.code for i in results["CP-01"]]
    assert "L09" not in codes


def test_linter_l09_no_issue_when_term_matches():
    case = _case("Validar que el sistema registre la exclusión cuando el beneficiario ya no aplica")
    results = lint_batch([case], glossary=GLOSSARY)
    codes = [i.code for i in results["CP-01"]]
    assert "L09" not in codes


def test_linter_l09_synonym_in_expected_result():
    case = _case(
        "Validar que el sistema genere la novedad cuando aplica",
        "El sistema registra la fecha efectiva en el contrato.",
    )
    results = lint_batch([case], glossary=GLOSSARY)
    codes = [i.code for i in results["CP-01"]]
    assert "L09" in codes


def test_linter_l09_no_false_positive_canonical():
    case = _case(
        "Validar que el sistema registre la fecha de efecto cuando cambia la IPS",
        "El sistema muestra la fecha de efecto actualizada.",
    )
    results = lint_batch([case], glossary=GLOSSARY)
    codes = [i.code for i in results["CP-01"]]
    assert "L09" not in codes

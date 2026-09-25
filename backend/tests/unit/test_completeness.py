"""Tests para app.context.domain.completeness (RF-10d)."""
import pytest
from app.context.domain.completeness import (
    check_bug_description,
    check_brecha_description,
    check_free_text,
    check_description,
    CompletenessFinding,
)

_LONG = "x" * 35  # más de _MIN_LENGTH (30)
_SHORT = "ok"     # menos de _MIN_LENGTH


class TestCheckBugDescription:
    def test_completo_sin_hallazgos(self):
        content = {
            "bug_behavior": _LONG,
            "what_to_test": _LONG,
            "expected_result": _LONG,
            "fix": _LONG,
        }
        assert check_bug_description(content) == []

    def test_falta_bug_behavior(self):
        content = {"bug_behavior": _SHORT, "what_to_test": _LONG, "expected_result": _LONG, "fix": _LONG}
        fields = [f.field for f in check_bug_description(content)]
        assert "bug_behavior" in fields

    def test_falta_what_to_test(self):
        content = {"bug_behavior": _LONG, "what_to_test": "", "expected_result": _LONG, "fix": _LONG}
        fields = [f.field for f in check_bug_description(content)]
        assert "what_to_test" in fields

    def test_falta_expected_result(self):
        content = {"bug_behavior": _LONG, "what_to_test": _LONG, "expected_result": None, "fix": _LONG}
        fields = [f.field for f in check_bug_description(content)]
        assert "expected_result" in fields

    def test_falta_fix(self):
        content = {"bug_behavior": _LONG, "what_to_test": _LONG, "expected_result": _LONG, "fix": ""}
        fields = [f.field for f in check_bug_description(content)]
        assert "fix" in fields

    def test_todo_vacio(self):
        content = {}
        findings = check_bug_description(content)
        assert len(findings) == 4

    def test_hallazgo_tiene_mensaje(self):
        content = {"bug_behavior": _SHORT, "what_to_test": _LONG, "expected_result": _LONG, "fix": _LONG}
        findings = check_bug_description(content)
        assert findings[0].message


class TestCheckBrechaDescription:
    def test_completo_sin_hallazgos(self):
        content = {
            "what_changes": _LONG,
            "what_to_test": _LONG,
            "expected_result": _LONG,
        }
        assert check_brecha_description(content) == []

    def test_falta_what_changes(self):
        content = {"what_changes": _SHORT, "what_to_test": _LONG, "expected_result": _LONG}
        fields = [f.field for f in check_brecha_description(content)]
        assert "what_changes" in fields

    def test_falta_what_to_test(self):
        content = {"what_changes": _LONG, "what_to_test": None, "expected_result": _LONG}
        fields = [f.field for f in check_brecha_description(content)]
        assert "what_to_test" in fields

    def test_falta_expected_result(self):
        content = {"what_changes": _LONG, "what_to_test": _LONG, "expected_result": ""}
        fields = [f.field for f in check_brecha_description(content)]
        assert "expected_result" in fields

    def test_todo_vacio(self):
        findings = check_brecha_description({})
        assert len(findings) == 3


class TestCheckFreeText:
    def test_texto_largo_sin_hallazgos(self):
        assert check_free_text(_LONG * 2) == []

    def test_texto_corto_hallazgo(self):
        findings = check_free_text("Muy corto")
        assert len(findings) == 1
        assert findings[0].field == "free_text"

    def test_texto_vacio_hallazgo(self):
        findings = check_free_text("")
        assert len(findings) == 1

    def test_solo_espacios_hallazgo(self):
        findings = check_free_text("   ")
        assert len(findings) == 1


class TestCheckDescription:
    def test_free_text_sobrescribe_guiado(self):
        content = {
            "free_text": _LONG * 2,
            "bug_behavior": _SHORT,
        }
        findings = check_description("bug", content)
        assert findings == []

    def test_free_text_corto_hallazgo(self):
        content = {"free_text": "Corto"}
        findings = check_description("bug", content)
        assert findings[0].field == "free_text"

    def test_bug_guiado(self):
        content = {"what_to_test": _LONG, "expected_result": _LONG, "fix": _LONG}
        findings = check_description("bug", content)
        fields = [f.field for f in findings]
        assert "bug_behavior" in fields

    def test_brecha_guiada(self):
        content = {"what_to_test": _LONG, "expected_result": _LONG}
        findings = check_description("brecha", content)
        fields = [f.field for f in findings]
        assert "what_changes" in fields

    def test_tipo_desconocido_usa_brecha(self):
        content = {}
        findings = check_description("otro", content)
        fields = [f.field for f in findings]
        assert "what_changes" in fields

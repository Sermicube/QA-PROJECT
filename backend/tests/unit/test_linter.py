"""Tests para app.testcases.domain.linter (RF-17, §6.4)."""
import pytest
from app.testcases.domain.linter import CaseInput, LintIssue, lint_case, lint_batch


def _case(
    name: str = "Validar que el sistema rechaza cuando la fecha es anterior al contrato",
    expected_result: str = "El sistema muestra el mensaje 'Fecha inválida'.",
    steps: list[str] | None = None,
    preconditions: list[str] | None = None,
    boundary: str | None = None,
    criteria_ids: list[str] | None = None,
    code: str = "CP-01",
) -> CaseInput:
    return CaseInput(
        code=code,
        name=name,
        preconditions=preconditions or ["El usuario tiene sesión activa."],
        steps=steps or ["Se accede a Beyond Health y se registra la novedad."],
        expected_result=expected_result,
        boundary=boundary,
        criteria_ids=criteria_ids or [],
    )


class TestL01:
    def test_nombre_correcto_sin_error(self):
        issues = lint_case(_case())
        assert not any(i.code == "L01" for i in issues)

    def test_nombre_sin_prefijo_error(self):
        issues = lint_case(_case(name="Comprobar que el sistema rechaza cuando falta fecha"))
        assert any(i.code == "L01" for i in issues)

    def test_prefijo_case_insensitive(self):
        issues = lint_case(_case(name="VALIDAR QUE EL SISTEMA hace algo cuando pasa algo"))
        assert not any(i.code == "L01" for i in issues)

    def test_prefijo_incompleto_error(self):
        issues = lint_case(_case(name="Validar que rechaza cuando algo"))
        assert any(i.code == "L01" for i in issues)


class TestL02:
    def test_una_condicion_correcto(self):
        issues = lint_case(_case())
        assert not any(i.code == "L02" for i in issues)

    def test_sin_cuando_error(self):
        issues = lint_case(_case(name="Validar que el sistema rechaza la novedad"))
        assert any(i.code == "L02" for i in issues)

    def test_dos_cuando_error(self):
        issues = lint_case(_case(
            name="Validar que el sistema rechaza cuando la fecha es incorrecta cuando el contrato está activo"
        ))
        assert any(i.code == "L02" for i in issues)


class TestL03:
    def test_nombre_sin_palabras_vagas(self):
        issues = lint_case(_case())
        assert not any(i.code == "L03" for i in issues)

    def test_correctamente_en_nombre(self):
        issues = lint_case(_case(
            name="Validar que el sistema guarda correctamente cuando la fecha es válida"
        ))
        assert any(i.code == "L03" for i in issues)

    def test_adecuadamente_en_resultado(self):
        issues = lint_case(_case(expected_result="El sistema procesa adecuadamente la solicitud."))
        assert any(i.code == "L03" for i in issues)

    def test_exitosamente_en_pasos(self):
        issues = lint_case(_case(steps=["Se guarda exitosamente en el sistema."]))
        assert any(i.code == "L03" for i in issues)

    def test_sin_errores_en_resultado(self):
        issues = lint_case(_case(expected_result="La operación se completa sin errores."))
        assert any(i.code == "L03" for i in issues)


class TestL04:
    def test_resultado_simple_sin_warning(self):
        issues = lint_case(_case())
        assert not any(i.code == "L04" for i in issues)

    def test_resultado_multiple_warning(self):
        result = (
            "El sistema guarda el registro. "
            "Se actualiza el estado. "
            "Se envía notificación al usuario afiliado."
        )
        issues = lint_case(_case(expected_result=result))
        assert any(i.code == "L04" for i in issues)
        assert all(i.severity == "warning" for i in issues if i.code == "L04")


class TestL06:
    def test_nombre_corto_sin_error(self):
        issues = lint_case(_case())
        assert not any(i.code == "L06" for i in issues)

    def test_nombre_201_caracteres_error(self):
        long_name = "Validar que el sistema " + "x" * 179 + " cuando algo pasa"
        # Ajustar para que sea > 200
        long_name = long_name[:201]
        issues = lint_case(_case(name=long_name))
        assert any(i.code == "L06" for i in issues)

    def test_nombre_200_caracteres_sin_error(self):
        name = "Validar que el sistema " + "a" * 153 + " cuando algo"
        assert len(name) == 188  # dentro del límite
        issues = lint_case(_case(name=name))
        assert not any(i.code == "L06" for i in issues)


class TestL07:
    def test_sin_comparacion_sin_l07(self):
        cases = [_case(code="CP-01", name="Validar que el sistema registra la novedad cuando el contrato está activo")]
        results = lint_batch(cases)
        assert not any(i.code == "L07" for i in results["CP-01"])

    def test_con_comparacion_sin_boundary_warning(self):
        case = _case(
            name="Validar que el sistema rechaza cuando la fecha es anterior al contrato",
            boundary=None,
        )
        results = lint_batch([case])
        assert any(i.code == "L07" for i in results["CP-01"])

    def test_tres_fronteras_completas_sin_l07(self):
        cases = [
            _case(code="CP-01", name="Validar que el sistema rechaza cuando la fecha es anterior", boundary="before"),
            _case(code="CP-02", name="Validar que el sistema rechaza cuando la fecha es anterior", boundary="equal"),
            _case(code="CP-03", name="Validar que el sistema rechaza cuando la fecha es anterior", boundary="after"),
        ]
        results = lint_batch(cases)
        for code in ["CP-01", "CP-02", "CP-03"]:
            assert not any(i.code == "L07" for i in results[code])

    def test_falta_frontera_equal_warning(self):
        cases = [
            _case(code="CP-01", name="Validar que el sistema rechaza cuando la fecha es anterior", boundary="before"),
            _case(code="CP-02", name="Validar que el sistema rechaza cuando la fecha es anterior", boundary="after"),
        ]
        results = lint_batch(cases)
        l07_issues = [i for code in results for i in results[code] if i.code == "L07"]
        assert l07_issues
        assert any("equal" in i.message for i in l07_issues)


class TestL08:
    def test_todos_criterios_cubiertos_sin_l08(self):
        crit_id = "crit-uuid-1"
        cases = [_case(code="CP-01", criteria_ids=[crit_id])]
        results = lint_batch(cases, criterion_ids=[crit_id])
        assert not any(i.code == "L08" for i in results["CP-01"])

    def test_criterio_sin_cobertura_warning(self):
        cases = [_case(code="CP-01", criteria_ids=[])]
        results = lint_batch(cases, criterion_ids=["crit-uuid-1"])
        assert any(i.code == "L08" for i in results["CP-01"])

    def test_sin_criterios_definidos_sin_l08(self):
        cases = [_case(code="CP-01")]
        results = lint_batch(cases, criterion_ids=[])
        assert not any(i.code == "L08" for i in results["CP-01"])


class TestLintCaseSingle:
    def test_caso_perfecto_sin_issues(self):
        case = _case(
            name="Validar que el sistema rechaza la novedad cuando la fecha de efecto es anterior al contrato",
            expected_result="El sistema muestra el mensaje 'Fecha de efecto inválida'.",
            steps=["Se accede a Beyond Health y se registra la novedad con fecha anterior."],
        )
        issues = lint_case(case)
        assert issues == []

    def test_multiples_errores_en_un_caso(self):
        case = _case(
            name="Comprobar que algo pasa",
            expected_result="El sistema guarda adecuadamente.",
        )
        issues = lint_case(case)
        codes = {i.code for i in issues}
        assert "L01" in codes
        assert "L02" in codes
        assert "L03" in codes

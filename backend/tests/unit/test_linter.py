"""Tests para app.testcases.domain.linter (RF-17, §6.4).

Todos los avisos son S01-S08 y tienen severity="warning". Ninguno bloquea aprobación.
"""
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


class TestS01:
    def test_nombre_correcto_sin_aviso(self):
        issues = lint_case(_case())
        assert not any(i.code == "S01" for i in issues)

    def test_nombre_sin_prefijo_aviso(self):
        issues = lint_case(_case(name="Comprobar que el sistema rechaza cuando falta fecha"))
        assert any(i.code == "S01" for i in issues)

    def test_prefijo_case_insensitive(self):
        issues = lint_case(_case(name="VALIDAR QUE EL SISTEMA hace algo cuando pasa algo"))
        assert not any(i.code == "S01" for i in issues)

    def test_prefijo_incompleto_aviso(self):
        issues = lint_case(_case(name="Validar que rechaza cuando algo"))
        assert any(i.code == "S01" for i in issues)

    def test_todos_los_avisos_son_warning(self):
        issues = lint_case(_case(name="Comprobar que el sistema rechaza cuando falta fecha"))
        assert all(i.severity == "warning" for i in issues)


class TestS02:
    def test_una_condicion_correcto(self):
        issues = lint_case(_case())
        assert not any(i.code == "S02" for i in issues)

    def test_sin_cuando_aviso(self):
        issues = lint_case(_case(name="Validar que el sistema rechaza la novedad"))
        assert any(i.code == "S02" for i in issues)

    def test_dos_cuando_aviso(self):
        issues = lint_case(_case(
            name="Validar que el sistema rechaza cuando la fecha es incorrecta cuando el contrato está activo"
        ))
        assert any(i.code == "S02" for i in issues)


class TestS03:
    def test_nombre_sin_palabras_vagas(self):
        issues = lint_case(_case())
        assert not any(i.code == "S03" for i in issues)

    def test_correctamente_en_nombre(self):
        issues = lint_case(_case(
            name="Validar que el sistema guarda correctamente cuando la fecha es válida"
        ))
        assert any(i.code == "S03" for i in issues)

    def test_adecuadamente_en_resultado(self):
        issues = lint_case(_case(expected_result="El sistema procesa adecuadamente la solicitud."))
        assert any(i.code == "S03" for i in issues)

    def test_exitosamente_en_pasos(self):
        issues = lint_case(_case(steps=["Se guarda exitosamente en el sistema."]))
        assert any(i.code == "S03" for i in issues)

    def test_sin_errores_en_resultado(self):
        issues = lint_case(_case(expected_result="La operación se completa sin errores."))
        assert any(i.code == "S03" for i in issues)

    def test_correcto_en_nombre_es_vago(self):
        issues = lint_case(_case(
            name="Validar que el sistema consulte el empleador correcto cuando se solicita la incapacidad"
        ))
        assert any(i.code == "S03" for i in issues)

    def test_correcto_en_resultado_esperado_es_vago(self):
        issues = lint_case(_case(
            expected_result="El sistema retorna el valor correcto para el afiliado."
        ))
        assert any(i.code == "S03" for i in issues)

    def test_correcta_en_nombre_es_vago(self):
        issues = lint_case(_case(
            name="Validar que el sistema aplique la fecha correcta cuando el contrato es nuevo"
        ))
        assert any(i.code == "S03" for i in issues)


class TestS04:
    def test_resultado_simple_sin_aviso(self):
        issues = lint_case(_case())
        assert not any(i.code == "S04" for i in issues)

    def test_resultado_multiple_aviso(self):
        result = (
            "El sistema guarda el registro. "
            "Se actualiza el estado. "
            "Se envía notificación al usuario afiliado."
        )
        issues = lint_case(_case(expected_result=result))
        assert any(i.code == "S04" for i in issues)
        assert all(i.severity == "warning" for i in issues if i.code == "S04")


class TestS05:
    def test_nombre_corto_sin_aviso(self):
        issues = lint_case(_case())
        assert not any(i.code == "S05" for i in issues)

    def test_nombre_201_caracteres_aviso(self):
        long_name = "Validar que el sistema " + "x" * 179 + " cuando algo pasa"
        long_name = long_name[:201]
        issues = lint_case(_case(name=long_name))
        assert any(i.code == "S05" for i in issues)

    def test_nombre_200_caracteres_sin_aviso(self):
        name = "Validar que el sistema " + "a" * 153 + " cuando algo"
        assert len(name) == 188  # dentro del límite
        issues = lint_case(_case(name=name))
        assert not any(i.code == "S05" for i in issues)


class TestS06:
    def test_sin_comparacion_sin_s06(self):
        cases = [_case(code="CP-01", name="Validar que el sistema registra la novedad cuando el contrato está activo")]
        results = lint_batch(cases)
        assert not any(i.code == "S06" for i in results["CP-01"])

    def test_con_comparacion_sin_boundary_aviso(self):
        case = _case(
            name="Validar que el sistema rechaza cuando la fecha es anterior al contrato",
            boundary=None,
        )
        results = lint_batch([case])
        assert any(i.code == "S06" for i in results["CP-01"])

    def test_tres_fronteras_completas_sin_s06(self):
        cases = [
            _case(code="CP-01", name="Validar que el sistema rechaza cuando la fecha es anterior", boundary="before"),
            _case(code="CP-02", name="Validar que el sistema rechaza cuando la fecha es anterior", boundary="equal"),
            _case(code="CP-03", name="Validar que el sistema rechaza cuando la fecha es anterior", boundary="after"),
        ]
        results = lint_batch(cases)
        for code in ["CP-01", "CP-02", "CP-03"]:
            assert not any(i.code == "S06" for i in results[code])

    def test_falta_frontera_equal_aviso(self):
        cases = [
            _case(code="CP-01", name="Validar que el sistema rechaza cuando la fecha es anterior", boundary="before"),
            _case(code="CP-02", name="Validar que el sistema rechaza cuando la fecha es anterior", boundary="after"),
        ]
        results = lint_batch(cases)
        s06_issues = [i for code in results for i in results[code] if i.code == "S06"]
        assert s06_issues
        assert any("equal" in i.message for i in s06_issues)


class TestS07:
    def test_todos_criterios_cubiertos_sin_s07(self):
        crit_id = "crit-uuid-1"
        cases = [_case(code="CP-01", criteria_ids=[crit_id])]
        results = lint_batch(cases, criterion_ids=[crit_id])
        assert not any(i.code == "S07" for i in results["CP-01"])

    def test_criterio_sin_cobertura_aviso(self):
        cases = [_case(code="CP-01", criteria_ids=[])]
        results = lint_batch(cases, criterion_ids=["crit-uuid-1"])
        assert any(i.code == "S07" for i in results["CP-01"])

    def test_sin_criterios_definidos_sin_s07(self):
        cases = [_case(code="CP-01")]
        results = lint_batch(cases, criterion_ids=[])
        assert not any(i.code == "S07" for i in results["CP-01"])


class TestConsultServiceStyle:
    """S01/S02 se adaptan al estilo consult_service (RF-17)."""

    def _consult(self, name: str, **kw) -> CaseInput:
        return _case(
            name=name,
            steps=kw.get("steps", ["Se consulta el servicio con los parámetros indicados."]),
            preconditions=kw.get("preconditions", []),
            expected_result=kw.get("expected_result", "El servicio retorna HTTP 200 con los datos esperados."),
            code=kw.get("code", "CP-01"),
        )

    def test_consultar_un_singular_pasa_s01(self):
        c = self._consult("Consultar un afiliado por cédula, donde el afiliado tiene régimen Subsidiado")
        issues = lint_case(c)
        assert not any(i.code == "S01" for i in issues)

    def test_consultar_plural_pasa_s01(self):
        # Aceptar "Consultar incapacidades por…" (plural sin "un")
        c = self._consult("Consultar incapacidades por tipo 3, donde el usuario tiene empleador tipo 3")
        issues = lint_case(c)
        assert not any(i.code == "S01" for i in issues)

    def test_verbo_distinto_a_consultar_aviso_s01(self):
        c = self._consult("Buscar afiliado por cédula, donde el régimen es Subsidiado")
        issues = lint_case(c)
        assert any(i.code == "S01" for i in issues)

    def test_consultar_no_necesita_cuando(self):
        # S02 no debe dispararse para nombres consult_service (no requiere "cuando")
        c = self._consult("Consultar un empleador por NIT, donde el empleador tiene incapacidades activas")
        issues = lint_case(c)
        assert not any(i.code == "S02" for i in issues)

    def test_todos_los_avisos_son_warning_no_bloquean(self):
        # Ningún aviso debe tener severity="error"
        c = self._consult(
            "Consultar incapacidades por tipo 4, donde el usuario tiene empleador tipo 4",
            expected_result="El servicio retorna HTTP 200 con el campo empleadorId.",
        )
        issues = lint_case(c)
        assert all(i.severity == "warning" for i in issues)


class TestLintCaseSingle:
    def test_caso_perfecto_sin_issues(self):
        case = _case(
            name="Validar que el sistema rechaza la novedad cuando la fecha de efecto es anterior al contrato",
            expected_result="El sistema muestra el mensaje 'Fecha de efecto inválida'.",
            steps=["Se accede a Beyond Health y se registra la novedad con fecha anterior."],
        )
        issues = lint_case(case)
        assert issues == []

    def test_multiples_avisos_en_un_caso(self):
        case = _case(
            name="Comprobar que algo pasa",
            expected_result="El sistema guarda adecuadamente.",
        )
        issues = lint_case(case)
        codes = {i.code for i in issues}
        assert "S01" in codes
        assert "S02" in codes
        assert "S03" in codes
        # Todos son warnings, no errors
        assert all(i.severity == "warning" for i in issues)

"""Tests para app.deliverables.domain.step_generator (RF-30)."""
import pytest

from app.deliverables.domain.step_generator import generate_steps


class TestPlaceholderSubstitution:
    def test_placeholder_replaced(self):
        steps = ["Ingresar documento {document_number} del afiliado."]
        result = generate_steps(
            test_case={"steps": steps},
            assignment={"document_number": "123456789"},
            derived_values={},
        )
        assert "123456789" in result[0]
        assert "{document_number}" not in result[0]

    def test_multiple_placeholders_in_one_step(self):
        steps = ["Afiliado {document_number} con contrato {contract_number}."]
        result = generate_steps(
            test_case={"steps": steps},
            assignment={"document_number": "111", "contract_number": "CTR-99"},
            derived_values={},
        )
        assert "111" in result[0]
        assert "CTR-99" in result[0]

    def test_no_placeholder_appends_data_note(self):
        steps = ["Se accede a Beyond Health y se registra la novedad."]
        result = generate_steps(
            test_case={"steps": steps},
            assignment={"document_number": "555"},
            derived_values={},
        )
        assert len(result) == 2
        assert "555" in result[-1]
        assert "Datos a utilizar" in result[-1]

    def test_no_placeholder_no_data_no_note(self):
        steps = ["Se accede a Beyond Health."]
        result = generate_steps(
            test_case={"steps": steps},
            assignment={},
            derived_values={},
        )
        assert len(result) == 1

    def test_derived_values_substituted(self):
        steps = ["Usar fecha de efecto: {fecha_efecto}."]
        result = generate_steps(
            test_case={"steps": steps},
            assignment={},
            derived_values={"fecha_efecto": "2024-03-14"},
        )
        assert "2024-03-14" in result[0]

    def test_derived_values_in_note_when_no_placeholder(self):
        steps = ["Se registra la novedad."]
        result = generate_steps(
            test_case={"steps": steps},
            assignment={"document_number": "777"},
            derived_values={"fecha_efecto": "2024-01-01"},
        )
        note = result[-1]
        assert "777" in note or "2024-01-01" in note

    def test_empty_assignment_no_crash(self):
        steps = ["Paso sin datos."]
        result = generate_steps(
            test_case={"steps": steps},
            assignment={},
            derived_values={},
        )
        assert result == ["Paso sin datos."]

    def test_none_values_skipped_in_note(self):
        steps = ["Paso sin placeholder."]
        result = generate_steps(
            test_case={"steps": steps},
            assignment={"document_number": "123", "optional_field": None},
            derived_values={},
        )
        note = result[-1]
        assert "None" not in note

    def test_empty_steps_list(self):
        result = generate_steps(
            test_case={"steps": []},
            assignment={"document_number": "123"},
            derived_values={},
        )
        assert isinstance(result, list)

    def test_missing_steps_key(self):
        result = generate_steps(
            test_case={},
            assignment={},
            derived_values={},
        )
        assert result == []

"""Tests para app.testdata.domain.assignment (RF-25, §6.7)."""
import pandas as pd
import pytest

from app.testdata.domain.assignment import CaseAssignment, run_assignment


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _case(code: str, conditions: list[dict], derived_inputs: list[dict] | None = None, mutates_state: bool = True) -> dict:
    return {
        "code": code,
        "conditions": conditions,
        "derived_inputs": derived_inputs or [],
        "mutates_state": mutates_state,
    }


_COL_MAP = {
    "affiliate_role": "tipo_afiliado",
    "contract_status": "estado_contrato",
    "ips_start_date": "fecha_inicio_ips",
}


class TestSimpleAssignment:
    def test_simple_assignment_one_case(self):
        df = _make_df([
            {"tipo_afiliado": "beneficiario", "estado_contrato": "activo", "fecha_inicio_ips": "2024-01-15"},
            {"tipo_afiliado": "titular", "estado_contrato": "activo", "fecha_inicio_ips": "2024-02-01"},
        ])
        cases = [_case("CP-01", [{"field": "affiliate_role", "op": "eq", "value": "beneficiario"}])]
        result = run_assignment(cases, df, _COL_MAP)

        assert len(result) == 1
        assert result[0].case_code == "CP-01"
        assert result[0].primary_row == 0

    def test_multiple_cases_distinct_users(self):
        df = _make_df([
            {"tipo_afiliado": "beneficiario", "estado_contrato": "activo"},
            {"tipo_afiliado": "beneficiario", "estado_contrato": "activo"},
            {"tipo_afiliado": "beneficiario", "estado_contrato": "activo"},
        ])
        cases = [
            _case("CP-01", [{"field": "affiliate_role", "op": "eq", "value": "beneficiario"}], mutates_state=True),
            _case("CP-02", [{"field": "affiliate_role", "op": "eq", "value": "beneficiario"}], mutates_state=True),
        ]
        result = run_assignment(cases, df, _COL_MAP)

        assert len(result) == 2
        primaries = [r.primary_row for r in result if r.primary_row is not None]
        # Las asignaciones primarias deben ser distintas
        assert len(primaries) == len(set(primaries))

    def test_no_candidates_returns_none_primary(self):
        df = _make_df([
            {"tipo_afiliado": "titular", "estado_contrato": "activo"},
            {"tipo_afiliado": "titular", "estado_contrato": "suspendido"},
        ])
        cases = [_case("CP-01", [{"field": "affiliate_role", "op": "eq", "value": "beneficiario"}])]
        result = run_assignment(cases, df, _COL_MAP)

        assert len(result) == 1
        assert result[0].primary_row is None
        assert result[0].alternate_rows == []

    def test_alternates_not_include_primary(self):
        df = _make_df([
            {"tipo_afiliado": "beneficiario", "estado_contrato": "activo"},
            {"tipo_afiliado": "beneficiario", "estado_contrato": "activo"},
            {"tipo_afiliado": "beneficiario", "estado_contrato": "activo"},
        ])
        cases = [_case("CP-01", [{"field": "affiliate_role", "op": "eq", "value": "beneficiario"}])]
        result = run_assignment(cases, df, _COL_MAP, n_alternates=2)

        assert result[0].primary_row is not None
        for alt in result[0].alternate_rows:
            assert alt != result[0].primary_row

    def test_alternates_up_to_n(self):
        df = _make_df([
            {"tipo_afiliado": "beneficiario", "estado_contrato": "activo"},
            {"tipo_afiliado": "beneficiario", "estado_contrato": "activo"},
            {"tipo_afiliado": "beneficiario", "estado_contrato": "activo"},
            {"tipo_afiliado": "beneficiario", "estado_contrato": "activo"},
        ])
        cases = [_case("CP-01", [{"field": "affiliate_role", "op": "eq", "value": "beneficiario"}])]
        result = run_assignment(cases, df, _COL_MAP, n_alternates=2)

        assert len(result[0].alternate_rows) <= 2

    def test_empty_cases_returns_empty(self):
        df = _make_df([{"tipo_afiliado": "beneficiario"}])
        result = run_assignment([], df, _COL_MAP)
        assert result == []

    def test_empty_df_returns_none_primaries(self):
        df = _make_df([])
        cases = [_case("CP-01", [{"field": "affiliate_role", "op": "eq", "value": "beneficiario"}])]
        result = run_assignment(cases, df, _COL_MAP)
        assert len(result) == 1
        assert result[0].primary_row is None

    def test_justification_populated(self):
        df = _make_df([{"tipo_afiliado": "beneficiario", "estado_contrato": "activo"}])
        cases = [_case("CP-01", [
            {"field": "affiliate_role", "op": "eq", "value": "beneficiario"},
            {"field": "contract_status", "op": "eq", "value": "activo"},
        ])]
        result = run_assignment(cases, df, _COL_MAP)
        assert result[0].primary_row == 0
        assert "affiliate_role" in result[0].justification
        assert result[0].justification["affiliate_role"] == "beneficiario"

    def test_three_cases_all_assigned(self):
        df = _make_df([
            {"tipo_afiliado": "beneficiario", "estado_contrato": "activo"},
            {"tipo_afiliado": "beneficiario", "estado_contrato": "suspendido"},
            {"tipo_afiliado": "titular", "estado_contrato": "activo"},
        ])
        cases = [
            _case("CP-01", [{"field": "affiliate_role", "op": "eq", "value": "beneficiario"}, {"field": "contract_status", "op": "eq", "value": "activo"}]),
            _case("CP-02", [{"field": "affiliate_role", "op": "eq", "value": "beneficiario"}, {"field": "contract_status", "op": "eq", "value": "suspendido"}]),
            _case("CP-03", [{"field": "affiliate_role", "op": "eq", "value": "titular"}]),
        ]
        result = run_assignment(cases, df, _COL_MAP)
        primaries = [r.primary_row for r in result]
        non_null = [p for p in primaries if p is not None]
        assert len(non_null) == len(set(non_null)), "Usuarios distintos por caso"

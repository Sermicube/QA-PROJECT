"""Tests para app.testdata.domain.filter (RF-24)."""
import math

import numpy as np
import pandas as pd
import pytest

from app.testdata.domain.filter import evaluate_condition, filter_candidates


def _row(**kwargs) -> pd.Series:
    return pd.Series(kwargs)


# ── evaluate_condition ────────────────────────────────────────────────────────

class TestEqOp:
    def test_eq_string(self):
        row = _row(estado="activo")
        assert evaluate_condition(row, {"field": "estado", "op": "eq", "value": "activo"})

    def test_eq_case_insensitive(self):
        row = _row(estado="Activo")
        assert evaluate_condition(row, {"field": "estado", "op": "eq", "value": "activo"})

    def test_eq_no_match(self):
        row = _row(estado="suspendido")
        assert not evaluate_condition(row, {"field": "estado", "op": "eq", "value": "activo"})

    def test_eq_null_field_false(self):
        row = _row(estado=None)
        assert not evaluate_condition(row, {"field": "estado", "op": "eq", "value": "activo"})


class TestNeOp:
    def test_ne_different(self):
        row = _row(estado="suspendido")
        assert evaluate_condition(row, {"field": "estado", "op": "ne", "value": "activo"})

    def test_ne_same(self):
        row = _row(estado="activo")
        assert not evaluate_condition(row, {"field": "estado", "op": "ne", "value": "activo"})


class TestInNotIn:
    def test_in_list(self):
        row = _row(rol="beneficiario")
        assert evaluate_condition(row, {"field": "rol", "op": "in", "value": ["titular", "beneficiario"]})

    def test_not_in_list(self):
        row = _row(rol="titular")
        assert not evaluate_condition(row, {"field": "rol", "op": "not_in", "value": ["titular", "beneficiario"]})

    def test_in_not_member(self):
        row = _row(rol="otro")
        assert not evaluate_condition(row, {"field": "rol", "op": "in", "value": ["titular", "beneficiario"]})

    def test_not_in_member(self):
        row = _row(rol="otro")
        assert evaluate_condition(row, {"field": "rol", "op": "not_in", "value": ["titular", "beneficiario"]})


class TestNullOps:
    def test_is_null_empty_string(self):
        row = _row(fecha="")
        assert evaluate_condition(row, {"field": "fecha", "op": "is_null"})

    def test_is_null_none(self):
        row = _row(fecha=None)
        assert evaluate_condition(row, {"field": "fecha", "op": "is_null"})

    def test_is_null_nan(self):
        row = _row(fecha=float("nan"))
        assert evaluate_condition(row, {"field": "fecha", "op": "is_null"})

    def test_not_null_with_value(self):
        row = _row(fecha="2024-01-15")
        assert evaluate_condition(row, {"field": "fecha", "op": "not_null"})

    def test_not_null_empty_fails(self):
        row = _row(fecha="")
        assert not evaluate_condition(row, {"field": "fecha", "op": "not_null"})


class TestGtLtOps:
    def test_gt_date(self):
        row = _row(fecha_inicio="2024-06-15")
        assert evaluate_condition(row, {"field": "fecha_inicio", "op": "gt", "value": "2024-01-01"})

    def test_lt_number(self):
        row = _row(monto="50")
        assert evaluate_condition(row, {"field": "monto", "op": "lt", "value": "100"})

    def test_gte_equal(self):
        row = _row(monto="100")
        assert evaluate_condition(row, {"field": "monto", "op": "gte", "value": "100"})

    def test_lte_equal(self):
        row = _row(fecha="2024-03-01")
        assert evaluate_condition(row, {"field": "fecha", "op": "lte", "value": "2024-03-01"})

    def test_gt_fails_when_equal(self):
        row = _row(monto="100")
        assert not evaluate_condition(row, {"field": "monto", "op": "gt", "value": "100"})


class TestBetween:
    def test_between_inclusive(self):
        row = _row(monto="50")
        assert evaluate_condition(row, {"field": "monto", "op": "between", "value": [10, 100]})

    def test_between_at_boundary(self):
        row = _row(monto="10")
        assert evaluate_condition(row, {"field": "monto", "op": "between", "value": [10, 100]})

    def test_between_outside(self):
        row = _row(monto="200")
        assert not evaluate_condition(row, {"field": "monto", "op": "between", "value": [10, 100]})


class TestContains:
    def test_contains_substring(self):
        row = _row(nombre="Juan Carlos Pérez")
        assert evaluate_condition(row, {"field": "nombre", "op": "contains", "value": "Carlos"})

    def test_contains_not_found(self):
        row = _row(nombre="Juan")
        assert not evaluate_condition(row, {"field": "nombre", "op": "contains", "value": "Carlos"})


class TestCompareTwoFields:
    def test_compare_two_fields_lt(self):
        row = _row(fecha_inicio="2024-01-01", fecha_fin="2024-12-31")
        assert evaluate_condition(row, {"field": "fecha_inicio", "op": "lt", "other_field": "fecha_fin"})

    def test_compare_two_fields_eq(self):
        row = _row(a="100", b="100")
        assert evaluate_condition(row, {"field": "a", "op": "eq", "other_field": "b"})

    def test_compare_two_fields_gt_false(self):
        row = _row(inicio="2024-12-31", fin="2024-01-01")
        assert not evaluate_condition(row, {"field": "inicio", "op": "lt", "other_field": "fin"})


# ── filter_candidates ─────────────────────────────────────────────────────────

class TestFilterCandidates:
    def _make_df(self):
        return pd.DataFrame([
            {"estado_contrato": "activo", "tipo_afiliado": "beneficiario", "fecha_inicio_ips": "2024-01-15"},
            {"estado_contrato": "activo", "tipo_afiliado": "titular", "fecha_inicio_ips": "2024-02-01"},
            {"estado_contrato": "suspendido", "tipo_afiliado": "beneficiario", "fecha_inicio_ips": "2023-06-01"},
            {"estado_contrato": "activo", "tipo_afiliado": "beneficiario", "fecha_inicio_ips": ""},
        ])

    def test_filter_returns_matching_rows(self):
        df = self._make_df()
        col_map = {"contract_status": "estado_contrato", "affiliate_role": "tipo_afiliado"}
        conditions = [
            {"field": "contract_status", "op": "eq", "value": "activo"},
            {"field": "affiliate_role", "op": "eq", "value": "beneficiario"},
        ]
        result = filter_candidates(df, conditions, col_map)
        assert len(result) == 2

    def test_filter_no_matches(self):
        df = self._make_df()
        col_map = {"contract_status": "estado_contrato"}
        conditions = [{"field": "contract_status", "op": "eq", "value": "terminado"}]
        result = filter_candidates(df, conditions, col_map)
        assert len(result) == 0

    def test_filter_with_null_condition(self):
        df = self._make_df()
        col_map = {"ips_start_date": "fecha_inicio_ips"}
        conditions = [{"field": "ips_start_date", "op": "is_null"}]
        result = filter_candidates(df, conditions, col_map)
        assert len(result) == 1

    def test_filter_empty_conditions_returns_all(self):
        df = self._make_df()
        result = filter_candidates(df, [], {})
        assert len(result) == len(df)

    def test_filter_preserves_original_index(self):
        df = self._make_df()
        col_map = {"contract_status": "estado_contrato"}
        conditions = [{"field": "contract_status", "op": "eq", "value": "suspendido"}]
        result = filter_candidates(df, conditions, col_map)
        assert 2 in result.index

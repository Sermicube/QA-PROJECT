"""Algoritmo de asignación óptima de usuarios de prueba (RF-25, §6.7)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from app.testdata.domain.dates import compute_derived
from app.testdata.domain.filter import filter_candidates


_INF_COST = 1e9


@dataclass
class CaseAssignment:
    case_code: str
    primary_row: int | None
    alternate_rows: list[int]
    justification: dict
    derived_values: dict
    cost: float


def _build_justification(row: pd.Series, col_map: dict[str, str], conditions: list[dict]) -> dict:
    """Construye el mapa field_key → valor que satisface la condición."""
    just: dict = {}
    for cond in conditions:
        key = cond["field"]
        col = col_map.get(key, key)
        val = row.get(col)
        just[key] = ("" if pd.isna(val) else str(val)) if val is not None else ""
    return just


def _compute_all_derived(row: pd.Series, derived_inputs: list[dict], col_map: dict[str, str]) -> dict:
    result: dict = {}
    for di in derived_inputs or []:
        name = di.get("name", "")
        computed = compute_derived(di, row, col_map)
        result[name] = str(computed) if computed is not None else None
    return result


def _noise_cost(row: pd.Series, all_conditions: list[list[dict]], own_idx: int, col_map: dict[str, str]) -> float:
    """Penaliza usuarios que tienen campos que podrían disparar condiciones de otros casos."""
    noise = 0.0
    for i, conditions in enumerate(all_conditions):
        if i == own_idx:
            continue
        for cond in conditions:
            col = col_map.get(cond["field"], cond["field"])
            val = row.get(col)
            if val is not None and str(val).strip():
                noise += 0.1
    return noise


def run_assignment(
    cases: list[dict],
    df: pd.DataFrame,
    col_map: dict[str, str],
    n_alternates: int = 2,
) -> list[CaseAssignment]:
    """Asigna un usuario distinto por caso (todos con mutates_state por defecto).

    cases: [{code, conditions, derived_inputs, mutates_state}]
    """
    if not cases or df.empty:
        return [
            CaseAssignment(
                case_code=c["code"],
                primary_row=None,
                alternate_rows=[],
                justification={},
                derived_values={},
                cost=_INF_COST,
            )
            for c in cases
        ]

    n_cases = len(cases)
    all_rows = list(df.index)
    n_rows = len(all_rows)
    row_pos = {orig_idx: pos for pos, orig_idx in enumerate(all_rows)}

    all_conditions = [c.get("conditions", []) for c in cases]

    # Candidatos por caso
    candidate_sets: list[set[int]] = []
    for case in cases:
        candidates_df = filter_candidates(df, case.get("conditions", []), col_map)
        candidate_sets.append(set(candidates_df.index.tolist()))

    # Matriz de costo (n_cases × n_rows)
    cost_matrix = np.full((n_cases, n_rows), _INF_COST)
    for ci, case in enumerate(cases):
        for orig_idx in candidate_sets[ci]:
            pos = row_pos[orig_idx]
            row = df.loc[orig_idx]
            noise = _noise_cost(row, all_conditions, ci, col_map)
            cost_matrix[ci, pos] = noise

    # Resolver con scipy (requiere matriz cuadrada o más columnas que filas)
    if n_rows < n_cases:
        # Pad con columnas de costo infinito
        pad = np.full((n_cases, n_cases - n_rows), _INF_COST)
        cost_matrix_sq = np.hstack([cost_matrix, pad])
    else:
        cost_matrix_sq = cost_matrix

    row_ind, col_ind = linear_sum_assignment(cost_matrix_sq)

    assignments: list[CaseAssignment] = []
    assigned_positions: set[int] = set()

    for ci, pi in zip(row_ind, col_ind):
        if pi >= n_rows or cost_matrix[ci, pi] >= _INF_COST:
            # Sin candidato
            assignments.append(CaseAssignment(
                case_code=cases[ci]["code"],
                primary_row=None,
                alternate_rows=[],
                justification={},
                derived_values={},
                cost=_INF_COST,
            ))
        else:
            assigned_positions.add(pi)
            orig_idx = all_rows[pi]
            row = df.loc[orig_idx]
            just = _build_justification(row, col_map, cases[ci].get("conditions", []))
            derived = _compute_all_derived(row, cases[ci].get("derived_inputs", []), col_map)

            # Suplentes: candidatos no asignados con menor costo
            alternates: list[int] = []
            alt_costs = sorted(
                [
                    (cost_matrix[ci, row_pos[orig]], orig)
                    for orig in candidate_sets[ci]
                    if row_pos[orig] not in assigned_positions and orig != orig_idx
                    and cost_matrix[ci, row_pos[orig]] < _INF_COST
                ],
                key=lambda x: x[0],
            )
            for _, alt_orig in alt_costs[:n_alternates]:
                alternates.append(alt_orig)
                assigned_positions.add(row_pos[alt_orig])

            assignments.append(CaseAssignment(
                case_code=cases[ci]["code"],
                primary_row=orig_idx,
                alternate_rows=alternates,
                justification=just,
                derived_values=derived,
                cost=float(cost_matrix[ci, pi]),
            ))

    return assignments

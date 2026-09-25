"""DSL de condiciones determinístico con pandas (RF-24). Sin eval() ni código generado."""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd


def _parse_date(val: object) -> date | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (date, datetime)):
        return val if isinstance(val, date) else val.date()
    s = str(val).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _coerce(val: object) -> object:
    """Intenta convertir string a número o fecha para comparación."""
    if pd.isna(val) if isinstance(val, float) else False:
        return None
    if isinstance(val, (int, float, date, datetime)):
        return val
    s = str(val).strip()
    if not s:
        return None
    # Intento número
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        pass
    # Intento fecha
    d = _parse_date(s)
    if d:
        return d
    return s


def _is_null(val: object) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and pd.isna(val):
        return True
    return str(val).strip() == ""


def evaluate_condition(row: pd.Series, cond: dict) -> bool:
    """Evalúa una condición del DSL sobre una fila. Devuelve True si se cumple."""
    field: str = cond["field"]
    op: str = cond["op"]
    col_val = row.get(field)

    if op == "is_null":
        return _is_null(col_val)
    if op == "not_null":
        return not _is_null(col_val)

    # Comparación entre dos campos
    if "other_field" in cond:
        other_val = row.get(cond["other_field"])
        a = _coerce(col_val)
        b = _coerce(other_val)
        if a is None or b is None:
            return False
        try:
            if op == "eq":
                return a == b
            if op == "ne":
                return a != b
            if op == "lt":
                return a < b  # type: ignore[operator]
            if op == "lte":
                return a <= b  # type: ignore[operator]
            if op == "gt":
                return a > b  # type: ignore[operator]
            if op == "gte":
                return a >= b  # type: ignore[operator]
        except TypeError:
            return False
        return False

    raw_value = cond.get("value")

    if op == "eq":
        if _is_null(col_val):
            return False
        return str(col_val).strip().lower() == str(raw_value).strip().lower()

    if op == "ne":
        if _is_null(col_val):
            return True
        return str(col_val).strip().lower() != str(raw_value).strip().lower()

    if op == "in":
        if _is_null(col_val):
            return False
        return str(col_val).strip().lower() in [str(v).strip().lower() for v in (raw_value or [])]

    if op == "not_in":
        if _is_null(col_val):
            return True
        return str(col_val).strip().lower() not in [str(v).strip().lower() for v in (raw_value or [])]

    if op == "contains":
        if _is_null(col_val):
            return False
        return str(raw_value).lower() in str(col_val).lower()

    # Comparaciones numéricas/fecha
    a = _coerce(col_val)
    b = _coerce(raw_value) if raw_value is not None else None
    if a is None:
        return False

    try:
        if op == "gt":
            return a > b  # type: ignore[operator]
        if op == "gte":
            return a >= b  # type: ignore[operator]
        if op == "lt":
            return a < b  # type: ignore[operator]
        if op == "lte":
            return a <= b  # type: ignore[operator]
        if op == "between":
            lo = _coerce(raw_value[0]) if isinstance(raw_value, (list, tuple)) else None
            hi = _coerce(raw_value[1]) if isinstance(raw_value, (list, tuple)) else None
            return lo is not None and hi is not None and lo <= a <= hi  # type: ignore[operator]
    except (TypeError, IndexError):
        return False

    return False


def filter_candidates(
    df: pd.DataFrame,
    conditions: list[dict],
    col_map: dict[str, str],
) -> pd.DataFrame:
    """Filtra filas que cumplen TODAS las condiciones (AND lógico).

    col_map: {domain_field_key → column_name_in_df}
    Las condiciones usan domain_field_keys; se traducen con col_map.
    """
    if not conditions:
        return df.copy()

    # Construir versión de condiciones con nombres de columna reales
    resolved: list[dict] = []
    for cond in conditions:
        c = dict(cond)
        key = c.get("field", "")
        c["field"] = col_map.get(key, key)
        if "other_field" in c:
            other = c["other_field"]
            c["other_field"] = col_map.get(other, other)
        resolved.append(c)

    mask = pd.Series([True] * len(df), index=df.index)
    for cond in resolved:
        col = cond.get("field", "")
        if col not in df.columns and cond["op"] not in ("is_null", "not_null"):
            mask[:] = False
            break
        col_mask = df.apply(lambda row, c=cond: evaluate_condition(row, c), axis=1)
        mask = mask & col_mask

    return df[mask].copy()

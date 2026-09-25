"""Cálculo de fechas derivadas con festivos de Colombia (RF-27)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import holidays
import pandas as pd
from dateutil.relativedelta import relativedelta


_CO_HOLIDAYS = holidays.Colombia()


def add_offset(base: date, offset: int, unit: str) -> date:
    """Calcula base + offset en la unidad indicada."""
    if unit == "calendar_days":
        return base + timedelta(days=offset)

    if unit == "months":
        return base + relativedelta(months=offset)

    if unit == "business_days":
        step = 1 if offset >= 0 else -1
        current = base
        remaining = abs(offset)
        while remaining > 0:
            current += timedelta(days=step)
            if current.weekday() < 5 and current not in _CO_HOLIDAYS:
                remaining -= 1
        return current

    raise ValueError(f"Unidad desconocida: {unit!r}. Usar 'calendar_days', 'business_days' o 'months'.")


def _parse_date_value(val: object) -> date | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # pandas Timestamp
    try:
        ts = pd.Timestamp(s)
        return ts.date()
    except Exception:
        return None


def compute_derived(
    derived_input: dict,
    row: pd.Series,
    col_map: dict[str, str],
) -> date | None:
    """Calcula el valor derivado a partir de una fila del DataFrame.

    derived_input: {"name": "...", "expr": {"base": <domain_field>, "offset": int, "unit": str}}
    """
    expr = derived_input.get("expr", {})
    base_field: str = expr.get("base", "")
    col_name = col_map.get(base_field, base_field)
    raw = row.get(col_name)
    base_date = _parse_date_value(raw)
    if base_date is None:
        return None
    offset = int(expr.get("offset", 0))
    unit = expr.get("unit", "calendar_days")
    return add_offset(base_date, offset, unit)

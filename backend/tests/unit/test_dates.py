"""Tests para app.testdata.domain.dates (RF-27)."""
from datetime import date

import pandas as pd
import pytest

from app.testdata.domain.dates import add_offset, compute_derived


class TestAddOffset:
    def test_calendar_days_positive(self):
        assert add_offset(date(2024, 1, 1), 5, "calendar_days") == date(2024, 1, 6)

    def test_calendar_days_negative(self):
        assert add_offset(date(2024, 1, 10), -3, "calendar_days") == date(2024, 1, 7)

    def test_calendar_days_zero(self):
        assert add_offset(date(2024, 6, 15), 0, "calendar_days") == date(2024, 6, 15)

    def test_calendar_days_crosses_month(self):
        assert add_offset(date(2024, 1, 30), 3, "calendar_days") == date(2024, 2, 2)

    def test_months_positive(self):
        assert add_offset(date(2024, 1, 15), 3, "months") == date(2024, 4, 15)

    def test_months_negative(self):
        assert add_offset(date(2024, 6, 1), -2, "months") == date(2024, 4, 1)

    def test_months_end_of_month(self):
        # 31 de enero + 1 mes = 28/29 febrero
        result = add_offset(date(2024, 1, 31), 1, "months")
        assert result.month == 2

    def test_business_days_skip_weekend(self):
        # 2024-01-05 es viernes; +1 día hábil = 2024-01-09 (martes)
        # porque 2024-01-08 (lunes) es festivo Colombia: Reyes Magos (primer lunes tras 6-ene)
        result = add_offset(date(2024, 1, 5), 1, "business_days")
        assert result == date(2024, 1, 9)

    def test_business_days_skip_saturday(self):
        # 2024-01-06 es sábado; el lunes = 2024-01-08
        # sábado +1 día hábil pasa por lunes
        result = add_offset(date(2024, 1, 6), 1, "business_days")
        assert result == date(2024, 1, 9)

    def test_business_days_negative(self):
        # 2024-01-09 es martes; -1 día hábil = viernes 2024-01-05
        # (2024-01-08 es festivo Reyes Magos)
        result = add_offset(date(2024, 1, 9), -1, "business_days")
        assert result == date(2024, 1, 5)

    def test_business_days_skip_holiday_colombia(self):
        # 2024-01-01 es festivo (Año Nuevo) en Colombia
        # 2023-12-29 (viernes) + 1 día hábil = 2024-01-02 (martes, no el lunes 1 enero)
        result = add_offset(date(2023, 12, 29), 1, "business_days")
        assert result == date(2024, 1, 2)

    def test_business_days_skip_independence_day(self):
        # 7 agosto 2024 es Batalla de Boyacá (festivo Colombia)
        # 2024-08-06 (martes) + 2 días hábiles → skip 7 (festivo) → 8 y 9
        result = add_offset(date(2024, 8, 6), 2, "business_days")
        # 7-ago es festivo, 8-ago y 9-ago son hábiles
        assert result == date(2024, 8, 9)

    def test_unknown_unit_raises(self):
        with pytest.raises(ValueError, match="Unidad desconocida"):
            add_offset(date(2024, 1, 1), 1, "semanas")


class TestComputeDerived:
    def _col_map(self):
        return {
            "ips_start_date": "fecha_inicio_ips",
            "contract_start_date": "fecha_inicio_contrato",
        }

    def test_calendar_days_from_row(self):
        row = pd.Series({"fecha_inicio_ips": "2024-03-15"})
        di = {"name": "fecha_efecto", "expr": {"base": "ips_start_date", "offset": -1, "unit": "calendar_days"}}
        result = compute_derived(di, row, self._col_map())
        assert result == date(2024, 3, 14)

    def test_business_days_from_row(self):
        row = pd.Series({"fecha_inicio_ips": "2024-01-08"})  # lunes
        di = {"name": "fecha_efecto", "expr": {"base": "ips_start_date", "offset": -1, "unit": "business_days"}}
        result = compute_derived(di, row, self._col_map())
        assert result == date(2024, 1, 5)  # viernes anterior

    def test_null_base_returns_none(self):
        row = pd.Series({"fecha_inicio_ips": ""})
        di = {"name": "fecha_efecto", "expr": {"base": "ips_start_date", "offset": -1, "unit": "calendar_days"}}
        result = compute_derived(di, row, self._col_map())
        assert result is None

    def test_date_formats_ddmmyyyy(self):
        row = pd.Series({"fecha_inicio_contrato": "15/06/2024"})
        di = {"name": "test", "expr": {"base": "contract_start_date", "offset": 0, "unit": "calendar_days"}}
        result = compute_derived(di, row, self._col_map())
        assert result == date(2024, 6, 15)

    def test_months_from_row(self):
        row = pd.Series({"fecha_inicio_contrato": "2024-01-01"})
        di = {"name": "test", "expr": {"base": "contract_start_date", "offset": 6, "unit": "months"}}
        result = compute_derived(di, row, self._col_map())
        assert result == date(2024, 7, 1)

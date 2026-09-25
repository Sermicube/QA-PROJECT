"""Carga y vista previa de bases de usuarios (RF-20, RF-21)."""
from __future__ import annotations

import io
from typing import Any

import pandas as pd


def detect_delimiter(sample: str) -> str:
    """Detecta el delimitador probando |, ;, ,, tab."""
    candidates = ["|", ";", ",", "\t"]
    best_delim = ","
    best_count = 0
    for delim in candidates:
        lines = [l for l in sample.splitlines() if l.strip()]
        if not lines:
            continue
        counts = [line.count(delim) for line in lines[:5]]
        if not counts:
            continue
        avg = sum(counts) / len(counts)
        # Homogeneidad: poca varianza entre líneas
        variance = sum((c - avg) ** 2 for c in counts) / len(counts)
        if avg > best_count and variance < avg + 1:
            best_count = avg
            best_delim = delim
    return best_delim


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def load_base(file_path: str, mime_type: str) -> pd.DataFrame:
    """Carga la base de usuarios y normaliza nombres de columna."""
    lower_path = file_path.lower()
    if mime_type in ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",) or lower_path.endswith(".xlsx"):
        df = pd.read_excel(file_path, engine="openpyxl", dtype=str)
    elif mime_type in ("application/vnd.ms-excel",) or lower_path.endswith(".xls"):
        df = pd.read_excel(file_path, engine="xlrd", dtype=str)
    else:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            sample = "".join(f.readline() for _ in range(5))
        delim = detect_delimiter(sample)
        df = pd.read_csv(file_path, sep=delim, dtype=str, encoding="utf-8", errors="replace")
    return _normalize_columns(df)


def load_base_from_bytes(data: bytes, mime_type: str, file_name: str) -> pd.DataFrame:
    """Carga directamente desde bytes."""
    lower_name = file_name.lower()
    if mime_type in ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",) or lower_name.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(data), engine="openpyxl", dtype=str)
    elif mime_type in ("application/vnd.ms-excel",) or lower_name.endswith(".xls"):
        df = pd.read_excel(io.BytesIO(data), engine="xlrd", dtype=str)
    else:
        sample_text = data[:2048].decode("utf-8", errors="replace")
        delim = detect_delimiter(sample_text)
        df = pd.read_csv(io.BytesIO(data), sep=delim, dtype=str, encoding="utf-8", errors="replace")
    return _normalize_columns(df)


def preview(df: pd.DataFrame, n: int = 10) -> list[dict[str, str]]:
    """Primeras n filas como lista de dicts con valores string."""
    rows: list[dict[str, str]] = []
    for _, row in df.head(n).iterrows():
        rows.append({col: ("" if pd.isna(val) else str(val)) for col, val in row.items()})
    return rows


def detect_column_types(df: pd.DataFrame) -> dict[str, str]:
    """Detecta el tipo semántico de cada columna."""
    result: dict[str, str] = {}
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            result[col] = "text"
            continue
        if pd.api.types.is_bool_dtype(series):
            result[col] = "boolean"
            continue
        if pd.api.types.is_numeric_dtype(series):
            result[col] = "number"
            continue
        # Intentar parsear como fecha
        parsed = pd.to_datetime(series, dayfirst=True, errors="coerce")
        if parsed.notna().mean() >= 0.8:
            result[col] = "date"
            continue
        # Detectar booleanos en texto
        lower_vals = series.str.lower().unique()
        bool_vals = {"si", "no", "sí", "true", "false", "1", "0", "s", "n"}
        if set(lower_vals).issubset(bool_vals):
            result[col] = "boolean"
            continue
        result[col] = "text"
    return result

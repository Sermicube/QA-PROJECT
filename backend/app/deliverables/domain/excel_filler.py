"""Llenado de la plantilla CO-FR-VRA-03 (RF-40).

Solo escribe valores; preserva estilos y fórmulas. Nunca altera el formato.
"""
from __future__ import annotations

from pathlib import Path


def fill_template(
    template_path: str,
    mapping_path: str,
    data: dict,
    output_path: str,
) -> None:
    """Rellena la plantilla Excel con los datos de la certificación.

    data keys esperadas:
    - requirement_code, module, analyst, date (str dd/mm/yyyy)
    - test_cases: list[{code, name, steps, expected_result, result}]
    """
    import shutil
    import yaml
    import openpyxl

    if not Path(template_path).exists():
        raise FileNotFoundError(f"Plantilla no encontrada: {template_path}")

    # Copiar plantilla para no modificar el original
    shutil.copy2(template_path, output_path)
    wb = openpyxl.load_workbook(output_path)

    with open(mapping_path, encoding="utf-8") as f:
        mapping = yaml.safe_load(f)

    # ── Campos individuales ────────────────────────────────────────────────────
    for field_name, cell_cfg in (mapping.get("fields") or {}).items():
        value = data.get(field_name)
        if value is None:
            continue
        sheet_name = cell_cfg["sheet"]
        cell_addr = cell_cfg["cell"]
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        ws[cell_addr] = value

    # ── Tablas ─────────────────────────────────────────────────────────────────
    for _table_name, tbl_cfg in (mapping.get("tables") or {}).items():
        sheet_name = tbl_cfg["sheet"]
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        start_row: int = tbl_cfg["start_row"]
        cols: dict[str, str] = tbl_cfg["columns"]
        rows = data.get("test_cases") or []

        for i, row_data in enumerate(rows):
            row_num = start_row + i
            for field, col_letter in cols.items():
                val = row_data.get(field)
                if val is None:
                    continue
                # Para listas (steps), unir con saltos de línea
                if isinstance(val, list):
                    val = "\n".join(str(v) for v in val)
                ws[f"{col_letter}{row_num}"] = str(val)

    wb.save(output_path)

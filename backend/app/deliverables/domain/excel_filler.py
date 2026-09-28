"""Llenado de la plantilla CO-FR-VRA-03 (RF-40).

Solo escribe valores en celdas específicas; preserva estilos, merges y
fórmulas. Nunca altera el formato del documento.
"""
from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path


def fill_co_fr_vra_03(
    template_path: str | Path,
    output_path: str | Path,
    *,
    title: str,
    external_code: str,
    module: str,
    cert_type: str,           # "bug" | "brecha"
    description: str,
    analyst_name: str,
    start_date: date,
    end_date: date,
    test_cases: list[dict],   # ver estructura abajo
    proyecto: str = "Vertical Salud",
) -> None:
    """Rellena la plantilla con los datos de la certificación.

    Estructura de cada elemento en test_cases:
    {
        "code": "CP1",
        "name": "Validar que ...",
        "objective": str | None,
        "preconditions": str | None,
        "input_data": str | None,
        "steps": list[str],
        "expected_result": str | None,
        "result": "passed" | "failed" | "blocked" | None,
        "observation": str | None,
        "evidence_description": str | None,
    }
    """
    import openpyxl
    from copy import copy as _copy

    tpl = Path(template_path)
    if not tpl.exists():
        raise FileNotFoundError(f"Plantilla no encontrada: {tpl}")

    shutil.copy2(tpl, output_path)
    wb = openpyxl.load_workbook(output_path)

    start_str = start_date.strftime("%d/%m/%Y")
    end_str = end_date.strftime("%d/%m/%Y")

    tipo_cambio = "Correctivos" if cert_type == "bug" else "Nueva Funcionalidad"

    # ── 1. Descripción del Desarrollo ─────────────────────────────────────────
    _fill_descripcion(wb, title, external_code, module, cert_type, description,
                      analyst_name, start_str, end_str, proyecto, tipo_cambio)

    # ── 2. Casos de Prueba (tabla resumen) ────────────────────────────────────
    _fill_casos_tabla(wb, test_cases, title)

    # ── 3. Pasos consolidados ─────────────────────────────────────────────────
    _fill_pasos(wb, test_cases)

    # ── 4. Hojas individuales CPx ─────────────────────────────────────────────
    existing_cp_sheets = [s for s in wb.sheetnames if s.startswith("CP") and s[2:].isdigit()]

    for i, tc in enumerate(test_cases, start=1):
        sheet_name = f"CP{i}"
        if sheet_name not in wb.sheetnames:
            # Copiar la primera hoja CP como plantilla para casos extras
            src_sheet = wb[existing_cp_sheets[0]] if existing_cp_sheets else None
            if src_sheet:
                new_ws = wb.copy_worksheet(src_sheet)
                new_ws.title = sheet_name
                # Mover al lugar correcto (antes de Control de revisiones)
                ctrl_idx = wb.sheetnames.index("Control de revisiones") if "Control de revisiones" in wb.sheetnames else len(wb.sheetnames)
                wb.move_sheet(sheet_name, offset=ctrl_idx - wb.sheetnames.index(sheet_name) - 1)
        _fill_cp_sheet(wb, sheet_name, title, tc, start_str)

    wb.save(output_path)


# ── helpers ───────────────────────────────────────────────────────────────────

def _safe_write(ws: object, addr: str, value: object) -> None:
    """Escribe solo si la celda no es MergedCell secundaria."""
    from openpyxl.cell.cell import MergedCell
    cell = ws[addr]
    if isinstance(cell, MergedCell):
        return
    cell.value = value


def _fill_descripcion(wb, title, code, module, cert_type, description,
                       analyst, start_str, end_str, proyecto, tipo_cambio):
    try:
        ws = wb["Descripción del Desarrollo"]
    except KeyError:
        return

    _safe_write(ws, "A7", title)
    _safe_write(ws, "D12", proyecto)
    _safe_write(ws, "B14", start_str)
    _safe_write(ws, "D14", code)
    _safe_write(ws, "K14", title)
    _safe_write(ws, "B15", end_str)
    _safe_write(ws, "A19", module)
    _safe_write(ws, "M19", tipo_cambio)

    # Tipo de cambio checkboxes: marcar el que aplica
    if cert_type == "bug":
        _safe_write(ws, "V22", "X")   # Correctivos
    else:
        _safe_write(ws, "V19", "X")   # Nueva Funcionalidad

    _safe_write(ws, "A21", description)
    _safe_write(ws, "A29", analyst)


def _result_label(result: str | None) -> str:
    mapping = {"passed": "Certificado", "failed": "Fallido", "blocked": "Bloqueado"}
    return mapping.get(result or "", "Pendiente")


def _fill_casos_tabla(wb, test_cases: list[dict], title: str) -> None:
    try:
        ws = wb["Casos de Prueba"]
    except KeyError:
        return

    _safe_write(ws, "A5", title)

    for i, tc in enumerate(test_cases, start=1):
        row = 6 + i  # datos empiezan en fila 7
        _safe_write(ws, f"A{row}", i)
        _safe_write(ws, f"B{row}", f"CP{i}")
        _safe_write(ws, f"C{row}", tc.get("name", ""))
        _safe_write(ws, f"D{row}", _result_label(tc.get("result")))
        _safe_write(ws, f"E{row}", 1 if tc.get("result") in ("passed", "failed") else 0)
        _safe_write(ws, f"F{row}", tc.get("observation") or "")


def _fill_pasos(wb, test_cases: list[dict]) -> None:
    try:
        ws = wb["Pasos"]
    except KeyError:
        return

    current_row = 4
    for i, tc in enumerate(test_cases, start=1):
        _safe_write(ws, f"A{current_row}", f"CASO {i}")
        _safe_write(ws, f"C{current_row}", tc.get("name", ""))
        current_row += 1

        _safe_write(ws, f"A{current_row}", "Pasos")
        _safe_write(ws, f"B{current_row}", "Tipo")
        _safe_write(ws, f"C{current_row}", "Acción")
        _safe_write(ws, f"D{current_row}", "Resultado esperado")
        current_row += 1

        steps = tc.get("steps") or []
        for j, step in enumerate(steps, start=1):
            _safe_write(ws, f"A{current_row}", j)
            _safe_write(ws, f"B{current_row}", "Funcional")
            _safe_write(ws, f"C{current_row}", str(step))
            current_row += 1

        current_row += 1  # línea en blanco entre casos


def _fill_cp_sheet(wb, sheet_name: str, title: str, tc: dict, date_str: str) -> None:
    try:
        ws = wb[sheet_name]
    except KeyError:
        return

    case_num = sheet_name  # "CP1", "CP2", etc.

    _safe_write(ws, "A1", title)
    _safe_write(ws, "B5", case_num)
    _safe_write(ws, "H5", tc.get("name", ""))
    _safe_write(ws, "D6", tc.get("objective") or tc.get("name", ""))
    _safe_write(ws, "D7", tc.get("preconditions") or "")
    _safe_write(ws, "D8", tc.get("input_data") or "")
    _safe_write(ws, "E9", date_str)
    _safe_write(ws, "A11", tc.get("name", ""))

    steps = tc.get("steps") or []
    for j, step in enumerate(steps):
        if j >= 12:
            break
        row = 13 + j
        _safe_write(ws, f"B{row}", str(step))

    # Resultado esperado en la última fila con paso, o fija en I16
    expected = tc.get("expected_result") or ""
    if steps:
        last_step_row = 13 + min(len(steps) - 1, 11)
        _safe_write(ws, f"I{last_step_row}", expected)
    else:
        _safe_write(ws, "I16", expected)

    # Observación (resultado real)
    obs = tc.get("observation") or ""
    result_label = _result_label(tc.get("result"))
    _safe_write(ws, "A25", f"Observación: {obs}" if obs else f"Estado: {result_label}")

    # Evidencia: descripción textual en B28
    ev_desc = tc.get("evidence_description") or ""
    if ev_desc:
        _safe_write(ws, "B28", ev_desc)


# ── Interfaz original con mapping YAML (conservada para compatibilidad) ───────

def fill_template(
    template_path: str,
    mapping_path: str,
    data: dict,
    output_path: str,
) -> None:
    """Rellena una plantilla Excel usando un mapping YAML genérico.

    Usado en tests unitarios y plantillas personalizadas. Para el
    CO-FR-VRA-03 oficial usar fill_co_fr_vra_03().
    """
    import shutil as _shutil
    import openpyxl as _opxl
    import yaml as _yaml

    if not Path(template_path).exists():
        raise FileNotFoundError(f"Plantilla no encontrada: {template_path}")

    _shutil.copy2(template_path, output_path)
    wb = _opxl.load_workbook(output_path)

    with open(mapping_path, encoding="utf-8") as f:
        mapping = _yaml.safe_load(f)

    for _field_name, cell_cfg in (mapping.get("fields") or {}).items():
        value = data.get(_field_name)
        if value is None:
            continue
        sheet_name = cell_cfg["sheet"]
        cell_addr = cell_cfg["cell"]
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        _safe_write(ws, cell_addr, value)

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
                if isinstance(val, list):
                    val = "\n".join(str(v) for v in val)
                _safe_write(ws, f"{col_letter}{row_num}", str(val))

    wb.save(output_path)

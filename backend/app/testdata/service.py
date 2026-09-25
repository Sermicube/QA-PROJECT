"""Lógica de negocio del módulo testdata (RF-20 a RF-29)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.storage import save_upload
from app.testdata.domain.assignment import run_assignment
from app.testdata.domain.loader import (
    detect_column_types,
    load_base_from_bytes,
    preview,
)
from app.testdata.domain.mapping import header_fingerprint
from app.testdata.domain.mapping import suggest_mapping_local
from app.testdata.models import Assignment, ColumnMapping, UserBase
from app.testdata.repository import TestDataRepository
from app.testdata.schemas import AssignmentOut, UserBasePreview


class TestDataError(Exception):
    pass


_DEFAULT_RETENTION_DAYS = 30


class TestDataService:
    def __init__(self, repo: TestDataRepository) -> None:
        self._repo = repo

    # ── RF-20 ─────────────────────────────────────────────────────────────────

    async def upload_base(
        self,
        cert_id: uuid.UUID,
        file_name: str,
        mime_type: str,
        data: bytes,
        owner_id: uuid.UUID,
        retention_days: int = _DEFAULT_RETENTION_DAYS,
    ) -> UserBase:
        df = load_base_from_bytes(data, mime_type, file_name)
        fingerprint = header_fingerprint(list(df.columns))
        row_count = len(df)
        file_path, stored_name = save_upload(cert_id, file_name, data)
        purge_after = datetime.now(timezone.utc) + timedelta(days=retention_days)
        base = await self._repo.create_base(
            cert_id=cert_id,
            file_path=file_path,
            file_name=file_name,
            fingerprint=fingerprint,
            row_count=row_count,
            purge_after=purge_after,
        )
        # Reutilizar mapeo si existe
        existing_mapping = await self._repo.find_mapping(fingerprint, owner_id)
        if existing_mapping:
            base = await self._repo.set_mapping(base.id, existing_mapping.id)
        return base

    # ── RF-21 ─────────────────────────────────────────────────────────────────

    async def preview_base(self, base_id: uuid.UUID) -> UserBasePreview:
        base = await self._repo.get_base(base_id)
        if base is None:
            raise TestDataError(f"Base {base_id} no encontrada")
        # Leer mime desde extensión
        mime = _mime_from_name(base.file_name)
        from app.testdata.domain.loader import load_base
        df = load_base(base.file_path, mime)
        col_types = detect_column_types(df)
        rows = preview(df, n=10)
        return UserBasePreview(
            id=base.id,
            file_name=base.file_name,
            row_count=base.row_count,
            headers=list(df.columns),
            types=col_types,
            rows=rows,
        )

    # ── RF-22 ─────────────────────────────────────────────────────────────────

    async def suggest_mapping_local(self, base_id: uuid.UUID) -> dict[str, str | None]:
        base = await self._repo.get_base(base_id)
        if base is None:
            raise TestDataError(f"Base {base_id} no encontrada")
        mime = _mime_from_name(base.file_name)
        from app.testdata.domain.loader import load_base
        df = load_base(base.file_path, mime)
        domain_fields = await self._repo.list_domain_fields()
        df_dicts = [{"key": f.key, "label": f.label, "synonyms": f.synonyms or []} for f in domain_fields]
        return suggest_mapping_local(list(df.columns), df_dicts)

    async def confirm_mapping(
        self,
        base_id: uuid.UUID,
        owner_id: uuid.UUID,
        module: str,
        mapping_dict: dict[str, str | None],
        col_types: dict[str, str] | None = None,
    ) -> ColumnMapping:
        base = await self._repo.get_base(base_id)
        if base is None:
            raise TestDataError(f"Base {base_id} no encontrada")
        fingerprint = base.header_fingerprint

        # Vocabulario extensible: crear campos de dominio desconocidos (RF-22)
        col_types = col_types or {}
        for col_name, field_key in mapping_dict.items():
            if field_key:
                detected_type = col_types.get(col_name, "text")
                await self._repo.get_or_create_domain_field(field_key, module, detected_type)

        cm = await self._repo.create_mapping(owner_id, fingerprint, module, mapping_dict)
        await self._repo.set_mapping(base_id, cm.id)
        return cm

    async def validate_conditions_fields(
        self,
        cert_id: uuid.UUID,
        conditions: list[dict],
    ) -> list[str]:
        """Devuelve los field keys de las condiciones que no están en el mapeo confirmado.

        Si no hay base con mapeo, devuelve lista vacía (no hay con qué validar).
        """
        available = await self._repo.get_available_fields_for_cert(cert_id)
        if available is None:
            return []
        available_keys = {f["key"] for f in available}
        invalid: list[str] = []
        for cond in conditions:
            field = cond.get("field")
            if field and field not in available_keys:
                invalid.append(field)
            other = cond.get("other_field")
            if other and other not in available_keys:
                invalid.append(other)
        return list(dict.fromkeys(invalid))  # deduplicar manteniendo orden

    # ── RF-24+25+26+27+28 ────────────────────────────────────────────────────

    async def run_assignment(
        self,
        cert_id: uuid.UUID,
        base_id: uuid.UUID,
    ) -> list[AssignmentOut]:
        base = await self._repo.get_base(base_id)
        if base is None:
            raise TestDataError(f"Base {base_id} no encontrada")
        if base.mapping_id is None:
            raise TestDataError("La base no tiene mapeo de columnas confirmado. Confirmar primero el mapeo.")

        # Cargar mapeo
        cm = base.mapping
        if cm is None:
            raise TestDataError("No se pudo cargar el mapeo de columnas.")
        col_map: dict[str, str] = {v: k for k, v in cm.mapping.items() if v}
        # col_map en run_assignment es {domain_field_key → col_name_in_df}
        col_map_domain_to_col = {v: k for k, v in cm.mapping.items() if v}

        # Cargar DataFrame
        mime = _mime_from_name(base.file_path)
        from app.testdata.domain.loader import load_base
        df = load_base(base.file_path, mime)

        # Cargar condiciones confirmadas para todos los casos aprobados de la cert
        from app.testcases.models import TestCase
        from sqlalchemy import select
        from app.core.db import async_session_factory

        conditions_list = await self._repo.list_conditions_for_cert(cert_id)

        # Verificar que todas las condiciones están confirmadas
        unconfirmed = [str(cc.test_case_id) for cc in conditions_list if not cc.confirmed]
        if unconfirmed:
            raise TestDataError(
                f"Los siguientes casos tienen condiciones sin confirmar: {', '.join(unconfirmed[:5])}. "
                "Confirmar las condiciones antes de ejecutar la asignación."
            )

        cases_data: list[dict[str, Any]] = []
        for cc in conditions_list:
            cases_data.append({
                "code": str(cc.test_case_id),
                "conditions": cc.conditions,
                "derived_inputs": cc.derived_inputs,
                "mutates_state": cc.mutates_state,
            })

        if not cases_data:
            return []

        assignments = run_assignment(cases_data, df, col_map_domain_to_col)

        # Persistir asignaciones y generar solicitudes de datos
        all_assignment_outs: list[AssignmentOut] = []
        data_requests: list[dict[str, Any]] = []

        for ca in assignments:
            tc_id = uuid.UUID(ca.case_code)
            if ca.primary_row is None:
                # RF-28: generar solicitud de datos
                cc_item = next((c for c in conditions_list if str(c.test_case_id) == ca.case_code), None)
                if cc_item:
                    text = _format_data_request(ca.case_code, cc_item.conditions, col_map_domain_to_col)
                    data_requests.append({"test_case_id": tc_id, "text": text})
                continue

            rows_to_save: list[dict[str, Any]] = [
                {
                    "row_ref": ca.primary_row,
                    "rank": 0,
                    "cost": ca.cost,
                    "justification": ca.justification,
                    "derived_values": ca.derived_values,
                }
            ]
            for i, alt in enumerate(ca.alternate_rows):
                rows_to_save.append({
                    "row_ref": alt,
                    "rank": i + 1,
                    "cost": 0.0,
                    "justification": {},
                    "derived_values": {},
                })

            saved = await self._repo.replace_assignments(tc_id, base_id, rows_to_save)
            for a in saved:
                all_assignment_outs.append(AssignmentOut.model_validate(a))

        await self._repo.replace_data_requests(cert_id, data_requests)

        return all_assignment_outs

    # ── RF-29 ─────────────────────────────────────────────────────────────────

    async def override_assignment(
        self,
        assignment_id: uuid.UUID,
        new_row_ref: int,
        justification: dict[str, Any] | None = None,
    ) -> Assignment:
        return await self._repo.override_assignment(
            assignment_id, new_row_ref, justification or {}
        )


# ── helpers ───────────────────────────────────────────────────────────────────

def _mime_from_name(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".xlsx"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if lower.endswith(".xls"):
        return "application/vnd.ms-excel"
    return "text/plain"


def _format_data_request(case_code: str, conditions: list[dict], col_map: dict[str, str]) -> str:
    lines = [f"Caso {case_code}: No se encontraron usuarios que cumplan todas las condiciones.", ""]
    lines.append("Condiciones requeridas:")
    for cond in conditions:
        field = cond.get("field", "?")
        op = cond.get("op", "?")
        val = cond.get("value", "")
        lines.append(f"  - {field} {op} {val}")
    lines.append("")
    lines.append("Solicitar usuarios de prueba que cumplan exactamente estas condiciones.")
    return "\n".join(lines)

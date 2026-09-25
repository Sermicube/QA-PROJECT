"""Lógica de negocio del módulo evidence (RF-31 a RF-34)."""
from __future__ import annotations

import uuid

from app.core.storage import save_upload
from app.evidence.models import Evidence, Execution
from app.evidence.repository import EvidenceRepository


class EvidenceError(Exception):
    pass


class EvidenceService:
    def __init__(self, repo: EvidenceRepository) -> None:
        self._repo = repo

    # RF-31
    async def upload_screenshot(
        self,
        tc_id: uuid.UUID,
        cert_id: uuid.UUID,
        file_name: str,
        mime_type: str,
        data: bytes,
    ) -> Evidence:
        file_path, _ = save_upload(cert_id, file_name, data)
        ev = await self._repo.add_evidence(tc_id, file_path, file_name, mime_type)
        return ev

    # RF-32
    async def accept_warning(self, evidence_id: uuid.UUID, reason: str) -> Evidence:
        ev = await self._repo.get_evidence(evidence_id)
        if ev is None:
            raise EvidenceError(f"Evidence {evidence_id} no encontrada")
        if ev.ocr_status not in ("warning", "rejected"):
            raise EvidenceError("Solo se puede aceptar evidencias con estado 'warning' o 'rejected'")
        return await self._repo.accept_warning(evidence_id, reason)

    # RF-34: caption local sin LLM
    async def generate_caption(self, evidence_id: uuid.UUID) -> Evidence:
        ev = await self._repo.get_evidence(evidence_id)
        if ev is None:
            raise EvidenceError(f"Evidence {evidence_id} no encontrada")

        # Obtener nombre del caso y resultado de ejecución
        from app.testcases.models import TestCase
        from app.evidence.models import Execution
        from sqlalchemy import select
        from app.core.db import async_session_factory

        tc_result = await self._repo._s.execute(
            select(TestCase).where(TestCase.id == ev.test_case_id)
        )
        tc = tc_result.scalar_one_or_none()

        exec_result = await self._repo._s.execute(
            select(Execution).where(Execution.test_case_id == ev.test_case_id)
        )
        execution = exec_result.scalar_one_or_none()

        case_name = tc.name if tc else "el caso de prueba"
        result_str = execution.result if execution else "pendiente"

        caption = f"Se muestra {case_name} con resultado {result_str}."
        return await self._repo.update_caption(evidence_id, caption)

    # RF-33
    async def record_execution(
        self,
        tc_id: uuid.UUID,
        result: str,
        observation: str | None,
    ) -> Execution:
        valid_results = {"passed", "failed", "blocked"}
        if result not in valid_results:
            raise EvidenceError(f"Resultado inválido: '{result}'. Debe ser uno de: {valid_results}")
        return await self._repo.upsert_execution(tc_id, result, observation)

"""Acceso a datos del módulo evidence."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.domain.ocr import OcrResult
from app.evidence.models import Evidence, Execution


class EvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── Evidence ──────────────────────────────────────────────────────────────

    async def add_evidence(
        self,
        tc_id: uuid.UUID,
        file_path: str,
        file_name: str,
        mime_type: str,
    ) -> Evidence:
        ev = Evidence(
            test_case_id=tc_id,
            file_path=file_path,
            file_name=file_name,
            mime_type=mime_type,
            ocr_status="pending",
        )
        self._s.add(ev)
        await self._s.flush()
        return ev

    async def get_evidence(self, evidence_id: uuid.UUID) -> Evidence | None:
        result = await self._s.execute(select(Evidence).where(Evidence.id == evidence_id))
        return result.scalar_one_or_none()

    async def update_ocr(self, evidence_id: uuid.UUID, result: OcrResult) -> Evidence:
        ev = await self.get_evidence(evidence_id)
        if ev is None:
            raise ValueError(f"Evidence {evidence_id} no encontrada")
        ev.ocr_status = result.status
        ev.ocr_time_found = result.time_found
        ev.ocr_url_found = result.url_found
        ev.ocr_time_value = result.time_value
        ev.ocr_url_value = result.url_value
        ev.updated_at = datetime.now(timezone.utc)
        await self._s.flush()
        return ev

    async def accept_warning(self, evidence_id: uuid.UUID, reason: str) -> Evidence:
        ev = await self.get_evidence(evidence_id)
        if ev is None:
            raise ValueError(f"Evidence {evidence_id} no encontrada")
        ev.accepted_with_reason = reason
        ev.ocr_status = "valid"
        ev.updated_at = datetime.now(timezone.utc)
        await self._s.flush()
        return ev

    async def update_caption(self, evidence_id: uuid.UUID, caption: str) -> Evidence:
        ev = await self.get_evidence(evidence_id)
        if ev is None:
            raise ValueError(f"Evidence {evidence_id} no encontrada")
        ev.caption = caption
        ev.updated_at = datetime.now(timezone.utc)
        await self._s.flush()
        return ev

    async def list_by_case(self, tc_id: uuid.UUID) -> list[Evidence]:
        result = await self._s.execute(
            select(Evidence).where(Evidence.test_case_id == tc_id).order_by(Evidence.created_at)
        )
        return list(result.scalars().all())

    async def list_by_cert(self, cert_id: uuid.UUID) -> list[Evidence]:
        from app.testcases.models import TestCase
        result = await self._s.execute(
            select(Evidence)
            .join(TestCase, TestCase.id == Evidence.test_case_id)
            .where(TestCase.certification_id == cert_id)
            .order_by(Evidence.created_at)
        )
        return list(result.scalars().all())

    # ── Execution ─────────────────────────────────────────────────────────────

    async def upsert_execution(
        self,
        tc_id: uuid.UUID,
        result: str,
        observation: str | None,
    ) -> Execution:
        existing = await self.get_execution(tc_id)
        now = datetime.now(timezone.utc)
        if existing:
            existing.result = result
            existing.observation = observation
            existing.executed_at = now
            existing.updated_at = now
            await self._s.flush()
            return existing
        ex = Execution(
            test_case_id=tc_id,
            result=result,
            observation=observation,
            executed_at=now,
        )
        self._s.add(ex)
        await self._s.flush()
        return ex

    async def get_execution(self, tc_id: uuid.UUID) -> Execution | None:
        result = await self._s.execute(
            select(Execution).where(Execution.test_case_id == tc_id)
        )
        return result.scalar_one_or_none()

    async def list_executions(self, cert_id: uuid.UUID) -> list[Execution]:
        from app.testcases.models import TestCase
        result = await self._s.execute(
            select(Execution)
            .join(TestCase, TestCase.id == Execution.test_case_id)
            .where(TestCase.certification_id == cert_id)
            .order_by(TestCase.order, TestCase.code)
        )
        return list(result.scalars().all())

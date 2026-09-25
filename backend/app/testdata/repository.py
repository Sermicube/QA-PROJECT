"""Acceso a datos del módulo testdata."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.testdata.models import (
    Assignment,
    CaseConditions,
    ColumnMapping,
    DataRequest,
    DomainField,
    UserBase,
)


class TestDataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── UserBase ──────────────────────────────────────────────────────────────

    async def create_base(
        self,
        cert_id: uuid.UUID,
        file_path: str,
        file_name: str,
        fingerprint: str,
        row_count: int,
        purge_after: datetime,
    ) -> UserBase:
        base = UserBase(
            certification_id=cert_id,
            file_path=file_path,
            file_name=file_name,
            header_fingerprint=fingerprint,
            row_count=row_count,
            purge_after=purge_after,
        )
        self._session.add(base)
        await self._session.flush()
        return base

    async def get_base(self, base_id: uuid.UUID) -> UserBase | None:
        result = await self._session.execute(select(UserBase).where(UserBase.id == base_id))
        return result.scalar_one_or_none()

    async def list_bases(self, cert_id: uuid.UUID) -> list[UserBase]:
        result = await self._session.execute(
            select(UserBase).where(UserBase.certification_id == cert_id).order_by(UserBase.created_at)
        )
        return list(result.scalars().all())

    async def set_mapping(self, base_id: uuid.UUID, mapping_id: uuid.UUID) -> UserBase:
        base = await self.get_base(base_id)
        if base is None:
            raise ValueError(f"UserBase {base_id} no encontrada")
        base.mapping_id = mapping_id
        base.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return base

    # ── ColumnMapping ─────────────────────────────────────────────────────────

    async def find_mapping(
        self, fingerprint: str, owner_id: uuid.UUID | None
    ) -> ColumnMapping | None:
        stmt = select(ColumnMapping).where(
            ColumnMapping.header_fingerprint == fingerprint,
        )
        if owner_id:
            stmt = stmt.where(
                (ColumnMapping.owner_id == owner_id) | (ColumnMapping.is_global == True)
            )
        else:
            stmt = stmt.where(ColumnMapping.is_global == True)
        stmt = stmt.order_by(ColumnMapping.is_global.asc())  # preferir propietario
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def create_mapping(
        self,
        owner_id: uuid.UUID | None,
        fingerprint: str,
        module: str,
        mapping_dict: dict[str, str | None],
    ) -> ColumnMapping:
        cm = ColumnMapping(
            owner_id=owner_id,
            header_fingerprint=fingerprint,
            module=module,
            mapping=mapping_dict,
        )
        self._session.add(cm)
        await self._session.flush()
        return cm

    async def list_domain_fields(self, module: str | None = None) -> list[DomainField]:
        stmt = select(DomainField)
        if module:
            stmt = stmt.where(DomainField.module == module)
        stmt = stmt.order_by(DomainField.key)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── CaseConditions ────────────────────────────────────────────────────────

    async def upsert_conditions(
        self,
        tc_id: uuid.UUID,
        conditions: list[dict],
        derived_inputs: list[dict],
        mutates_state: bool,
    ) -> CaseConditions:
        existing = await self.get_conditions(tc_id)
        if existing:
            existing.conditions = conditions
            existing.derived_inputs = derived_inputs
            existing.mutates_state = mutates_state
            existing.confirmed = False
            existing.updated_at = datetime.now(timezone.utc)
            await self._session.flush()
            return existing
        cc = CaseConditions(
            test_case_id=tc_id,
            conditions=conditions,
            derived_inputs=derived_inputs,
            mutates_state=mutates_state,
        )
        self._session.add(cc)
        await self._session.flush()
        return cc

    async def confirm_conditions(self, tc_id: uuid.UUID) -> CaseConditions:
        cc = await self.get_conditions(tc_id)
        if cc is None:
            raise ValueError(f"No hay condiciones para case {tc_id}")
        cc.confirmed = True
        cc.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return cc

    async def get_conditions(self, tc_id: uuid.UUID) -> CaseConditions | None:
        result = await self._session.execute(
            select(CaseConditions).where(CaseConditions.test_case_id == tc_id)
        )
        return result.scalar_one_or_none()

    async def list_conditions_for_cert(self, cert_id: uuid.UUID) -> list[CaseConditions]:
        from app.testcases.models import TestCase
        result = await self._session.execute(
            select(CaseConditions)
            .join(TestCase, TestCase.id == CaseConditions.test_case_id)
            .where(TestCase.certification_id == cert_id)
            .order_by(TestCase.order, TestCase.code)
        )
        return list(result.scalars().all())

    # ── Assignments ───────────────────────────────────────────────────────────

    async def replace_assignments(
        self,
        tc_id: uuid.UUID,
        base_id: uuid.UUID,
        assignments: list[dict[str, Any]],
    ) -> list[Assignment]:
        await self._session.execute(
            delete(Assignment).where(Assignment.test_case_id == tc_id)
        )
        result: list[Assignment] = []
        for a in assignments:
            obj = Assignment(
                test_case_id=tc_id,
                user_base_id=base_id,
                row_ref=a["row_ref"],
                rank=a["rank"],
                cost=a.get("cost", 0.0),
                justification=a.get("justification", {}),
                derived_values=a.get("derived_values", {}),
            )
            self._session.add(obj)
            result.append(obj)
        await self._session.flush()
        return result

    async def list_assignments(self, cert_id: uuid.UUID) -> list[Assignment]:
        from app.testcases.models import TestCase
        result = await self._session.execute(
            select(Assignment)
            .join(TestCase, TestCase.id == Assignment.test_case_id)
            .where(TestCase.certification_id == cert_id)
            .order_by(TestCase.order, TestCase.code, Assignment.rank)
        )
        return list(result.scalars().all())

    async def get_assignment(self, assignment_id: uuid.UUID) -> Assignment | None:
        result = await self._session.execute(
            select(Assignment).where(Assignment.id == assignment_id)
        )
        return result.scalar_one_or_none()

    async def override_assignment(
        self,
        assignment_id: uuid.UUID,
        new_row_ref: int,
        justification: dict[str, Any],
    ) -> Assignment:
        a = await self.get_assignment(assignment_id)
        if a is None:
            raise ValueError(f"Assignment {assignment_id} no encontrado")
        a.row_ref = new_row_ref
        a.justification = justification
        a.manual_override = True
        a.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return a

    # ── DataRequests ──────────────────────────────────────────────────────────

    async def replace_data_requests(
        self,
        cert_id: uuid.UUID,
        requests: list[dict[str, Any]],
    ) -> list[DataRequest]:
        await self._session.execute(
            delete(DataRequest).where(DataRequest.certification_id == cert_id)
        )
        result: list[DataRequest] = []
        for r in requests:
            obj = DataRequest(
                certification_id=cert_id,
                test_case_id=r["test_case_id"],
                text=r["text"],
            )
            self._session.add(obj)
            result.append(obj)
        await self._session.flush()
        return result

    async def list_data_requests(self, cert_id: uuid.UUID) -> list[DataRequest]:
        result = await self._session.execute(
            select(DataRequest).where(DataRequest.certification_id == cert_id).order_by(DataRequest.created_at)
        )
        return list(result.scalars().all())

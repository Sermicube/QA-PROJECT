"""Acceso a datos del módulo deliverables."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deliverables.models import Deliverable, Template


class DeliverableRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert(
        self,
        cert_id: uuid.UUID,
        kind: str,
        file_path: str | None = None,
        content: str | None = None,
    ) -> Deliverable:
        result = await self._s.execute(
            select(Deliverable).where(
                Deliverable.certification_id == cert_id,
                Deliverable.kind == kind,
            )
        )
        existing = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if existing:
            if file_path is not None:
                existing.file_path = file_path
            if content is not None:
                existing.content = content
            existing.generated_at = now
            existing.updated_at = now
            await self._s.flush()
            return existing
        d = Deliverable(
            certification_id=cert_id,
            kind=kind,
            file_path=file_path,
            content=content,
            generated_at=now,
        )
        self._s.add(d)
        await self._s.flush()
        return d

    async def list_by_cert(self, cert_id: uuid.UUID) -> list[Deliverable]:
        result = await self._s.execute(
            select(Deliverable)
            .where(Deliverable.certification_id == cert_id)
            .order_by(Deliverable.kind)
        )
        return list(result.scalars().all())

    async def get(self, deliverable_id: uuid.UUID) -> Deliverable | None:
        result = await self._s.execute(
            select(Deliverable).where(Deliverable.id == deliverable_id)
        )
        return result.scalar_one_or_none()

    async def get_template(
        self, kind: str, owner_id: uuid.UUID | None = None
    ) -> Template | None:
        stmt = select(Template).where(Template.kind == kind)
        if owner_id:
            stmt = stmt.where(
                (Template.owner_id == owner_id) | (Template.is_global == True)
            )
        else:
            stmt = stmt.where(Template.is_global == True)
        stmt = stmt.order_by(Template.is_global.asc())
        result = await self._s.execute(stmt)
        return result.scalars().first()

    async def create_template(
        self,
        kind: str,
        name: str,
        file_path: str,
        mapping: dict,
        owner_id: uuid.UUID | None = None,
        is_global: bool = False,
    ) -> Template:
        t = Template(
            kind=kind,
            name=name,
            file_path=file_path,
            mapping=mapping,
            is_global=is_global,
            owner_id=owner_id,
        )
        self._s.add(t)
        await self._s.flush()
        return t

    async def list_templates(self, kind: str | None = None) -> list[Template]:
        stmt = select(Template)
        if kind:
            stmt = stmt.where(Template.kind == kind)
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

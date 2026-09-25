import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.models import (
    AcceptanceCriterion,
    Ambiguity,
    CompletenessFinding,
    ContextSource,
)


class ContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── ContextSource ────────────────────────────────────────────────────────

    async def upsert_source(
        self,
        certification_id: uuid.UUID,
        kind: str,
        **kwargs: object,
    ) -> ContextSource:
        """Crea o actualiza la fuente del tipo indicado (una por tipo por certificación)."""
        q = select(ContextSource).where(
            ContextSource.certification_id == certification_id,
            ContextSource.kind == kind,
        )
        result = await self._s.execute(q)
        source = result.scalar_one_or_none()

        if source is None:
            source = ContextSource(certification_id=certification_id, kind=kind)
            self._s.add(source)
            await self._s.flush()

        for k, v in kwargs.items():
            setattr(source, k, v)

        await self._s.commit()
        await self._s.refresh(source)
        return source

    async def get_sources(self, certification_id: uuid.UUID) -> list[ContextSource]:
        q = select(ContextSource).where(ContextSource.certification_id == certification_id)
        result = await self._s.execute(q)
        return list(result.scalars().all())

    async def get_source(self, source_id: uuid.UUID) -> Optional[ContextSource]:
        q = select(ContextSource).where(ContextSource.id == source_id)
        result = await self._s.execute(q)
        return result.scalar_one_or_none()

    async def delete_source(self, source: ContextSource) -> None:
        await self._s.delete(source)
        await self._s.commit()

    # ── CompletenessFinding ──────────────────────────────────────────────────

    async def replace_findings(
        self,
        certification_id: uuid.UUID,
        source_id: uuid.UUID,
        findings: list[dict],
    ) -> list[CompletenessFinding]:
        # Borrar anteriores para esta fuente
        q = select(CompletenessFinding).where(CompletenessFinding.source_id == source_id)
        result = await self._s.execute(q)
        for old in result.scalars().all():
            await self._s.delete(old)

        new_objects: list[CompletenessFinding] = []
        for f in findings:
            obj = CompletenessFinding(
                certification_id=certification_id,
                source_id=source_id,
                field=f["field"],
                message=f["message"],
            )
            self._s.add(obj)
            new_objects.append(obj)

        await self._s.commit()
        for obj in new_objects:
            await self._s.refresh(obj)
        return new_objects

    async def dismiss_finding(self, finding_id: uuid.UUID) -> Optional[CompletenessFinding]:
        q = select(CompletenessFinding).where(CompletenessFinding.id == finding_id)
        result = await self._s.execute(q)
        finding = result.scalar_one_or_none()
        if finding:
            finding.dismissed = True
            await self._s.commit()
            await self._s.refresh(finding)
        return finding

    # ── AcceptanceCriterion ──────────────────────────────────────────────────

    async def replace_criteria(
        self, certification_id: uuid.UUID, criteria: list[dict]
    ) -> list[AcceptanceCriterion]:
        q = select(AcceptanceCriterion).where(
            AcceptanceCriterion.certification_id == certification_id
        )
        result = await self._s.execute(q)
        for old in result.scalars().all():
            await self._s.delete(old)

        objects: list[AcceptanceCriterion] = []
        for c in criteria:
            obj = AcceptanceCriterion(
                certification_id=certification_id,
                code=c["code"],
                text=c["text"],
                source_kind=c["source_kind"],
                source_section=c.get("source_section"),
            )
            self._s.add(obj)
            objects.append(obj)

        await self._s.commit()
        for obj in objects:
            await self._s.refresh(obj)
        return objects

    async def get_criteria(self, certification_id: uuid.UUID) -> list[AcceptanceCriterion]:
        q = select(AcceptanceCriterion).where(
            AcceptanceCriterion.certification_id == certification_id
        ).order_by(AcceptanceCriterion.code)
        result = await self._s.execute(q)
        return list(result.scalars().all())

    # ── Ambiguity ────────────────────────────────────────────────────────────

    async def add_ambiguities(
        self, certification_id: uuid.UUID, items: list[dict]
    ) -> list[Ambiguity]:
        objects: list[Ambiguity] = []
        for a in items:
            obj = Ambiguity(
                certification_id=certification_id,
                type=a["type"],
                fragment=a["fragment"],
                location=a["location"],
                explanation=a["explanation"],
                question=a["question"],
            )
            self._s.add(obj)
            objects.append(obj)

        await self._s.commit()
        for obj in objects:
            await self._s.refresh(obj)
        return objects

    async def clear_ambiguities(self, certification_id: uuid.UUID) -> None:
        q = select(Ambiguity).where(Ambiguity.certification_id == certification_id)
        result = await self._s.execute(q)
        for a in result.scalars().all():
            await self._s.delete(a)
        await self._s.commit()

    async def get_ambiguities(self, certification_id: uuid.UUID) -> list[Ambiguity]:
        q = select(Ambiguity).where(
            Ambiguity.certification_id == certification_id
        ).order_by(Ambiguity.created_at)
        result = await self._s.execute(q)
        return list(result.scalars().all())

    async def resolve_ambiguity(
        self,
        ambiguity_id: uuid.UUID,
        resolution: str,
        resolved_by: str,
    ) -> Optional[Ambiguity]:
        q = select(Ambiguity).where(Ambiguity.id == ambiguity_id)
        result = await self._s.execute(q)
        amb = result.scalar_one_or_none()
        if amb:
            amb.resolution = resolution
            amb.resolved_by = resolved_by
            amb.resolved_at = datetime.now(UTC)
            await self._s.commit()
            await self._s.refresh(amb)
        return amb

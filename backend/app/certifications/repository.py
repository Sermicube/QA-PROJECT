import uuid
from datetime import UTC, datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.certifications.models import Certification, StageEvent

# Raw SQL queries used to check whether a stage already has associated data.
# Stages with no dedicated table (format, analysis, review) are absent → return False.
_STAGE_DATA_QUERIES: dict[str, str] = {
    "context": (
        "SELECT COUNT(*) FROM context_sources WHERE certification_id = :cid"
    ),
    "testcases": (
        "SELECT COUNT(*) FROM test_cases WHERE certification_id = :cid"
    ),
    "data_request": (
        "SELECT COUNT(*) FROM data_requests WHERE certification_id = :cid"
    ),
    "assignment": (
        "SELECT COUNT(*) FROM user_bases WHERE certification_id = :cid"
    ),
    "execution": (
        "SELECT COUNT(*) FROM executions e "
        "JOIN test_cases tc ON tc.id = e.test_case_id "
        "WHERE tc.certification_id = :cid"
    ),
    "documentation": (
        "SELECT COUNT(*) FROM deliverables WHERE certification_id = :cid"
    ),
}


class CertificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        owner_id: uuid.UUID,
        type: str,
        external_code: str,
        module: str,
        title: str,
        *,
        description: Optional[str] = None,
        service: Optional[str] = None,
        recipe_code: Optional[str] = None,
        active_stages: Optional[dict] = None,
        case_style: Optional[str] = None,
        evidence_style: Optional[str] = None,
        execution_channel: Optional[str] = None,
        data_origin: Optional[str] = None,
    ) -> Certification:
        cert = Certification(
            owner_id=owner_id,
            type=type,
            external_code=external_code,
            module=module,
            title=title,
            description=description,
            service=service,
            recipe_code=recipe_code,
            active_stages=active_stages,
            case_style=case_style,
            evidence_style=evidence_style,
            execution_channel=execution_channel,
            data_origin=data_origin,
        )
        self._session.add(cert)
        await self._session.flush()
        event = StageEvent(
            certification_id=cert.id,
            stage=cert.stage,
            status="executed",
            source="recipe",
        )
        self._session.add(event)
        await self._session.commit()
        await self._session.refresh(cert)
        return cert

    async def get_by_id(
        self, cert_id: uuid.UUID, owner_id: Optional[uuid.UUID] = None
    ) -> Optional[Certification]:
        q = select(Certification).where(Certification.id == cert_id)
        if owner_id is not None:
            q = q.where(Certification.owner_id == owner_id)
        result = await self._session.execute(q)
        return result.scalar_one_or_none()

    async def list_by_owner(
        self,
        owner_id: uuid.UUID,
        *,
        type: Optional[str] = None,
        module: Optional[str] = None,
        stage: Optional[str] = None,
        status: Optional[str] = None,
        recipe_code: Optional[str] = None,
    ) -> list[Certification]:
        q = select(Certification).where(Certification.owner_id == owner_id)
        if type:
            q = q.where(Certification.type == type)
        if module:
            q = q.where(Certification.module == module)
        if stage:
            q = q.where(Certification.stage == stage)
        if status:
            q = q.where(Certification.status == status)
        if recipe_code:
            q = q.where(Certification.recipe_code == recipe_code)
        q = q.order_by(Certification.created_at.desc())
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def list_all_with_analyst_email(
        self,
        *,
        type: Optional[str] = None,
        module: Optional[str] = None,
        stage: Optional[str] = None,
        status: Optional[str] = None,
        recipe_code: Optional[str] = None,
    ) -> list[tuple["Certification", str]]:
        from app.users.models import User
        q = (
            select(Certification, User.email)
            .join(User, User.id == Certification.owner_id)
        )
        if type:
            q = q.where(Certification.type == type)
        if module:
            q = q.where(Certification.module == module)
        if stage:
            q = q.where(Certification.stage == stage)
        if status:
            q = q.where(Certification.status == status)
        if recipe_code:
            q = q.where(Certification.recipe_code == recipe_code)
        q = q.order_by(Certification.created_at.desc())
        result = await self._session.execute(q)
        return [(row.Certification, row.email) for row in result]

    async def update_stage(self, cert: Certification, new_stage: str) -> Certification:
        current_event = next(
            (e for e in cert.stage_events if e.stage == cert.stage and e.ended_at is None),
            None,
        )
        if current_event is not None:
            current_event.ended_at = datetime.now(UTC)
            current_event.status = "executed"

        cert.stage = new_stage
        if new_stage == "closed":
            cert.status = "closed"
            cert.closed_at = datetime.now(UTC)

        new_event = StageEvent(
            certification_id=cert.id,
            stage=new_stage,
            status="executed",
            source="recipe",
        )
        self._session.add(new_event)
        await self._session.commit()
        await self._session.refresh(cert)
        return cert

    async def add_stage(self, cert: Certification, stage: str) -> Certification:
        """Activate an optional or not_applicable stage. Records stage_added event."""
        if cert.active_stages is None:
            cert.active_stages = {}
        cert.active_stages = {**cert.active_stages, stage: "optional"}
        event = StageEvent(
            certification_id=cert.id,
            stage=stage,
            status="stage_added",
            source="analyst",
        )
        self._session.add(event)
        await self._session.commit()
        await self._session.refresh(cert)
        return cert

    async def remove_stage(self, cert: Certification, stage: str) -> Certification:
        """Deactivate an optional stage. Records stage_removed event."""
        if cert.active_stages is None:
            cert.active_stages = {}
        cert.active_stages = {**cert.active_stages, stage: "not_applicable"}
        event = StageEvent(
            certification_id=cert.id,
            stage=stage,
            status="stage_removed",
            source="analyst",
        )
        self._session.add(event)
        await self._session.commit()
        await self._session.refresh(cert)
        return cert

    async def update_active_stages(self, cert: Certification, active_stages: dict) -> Certification:
        cert.active_stages = active_stages
        await self._session.commit()
        await self._session.refresh(cert)
        return cert

    async def apply_origin_stage_changes(
        self,
        cert: Certification,
        new_stages: dict,
        promoted_stages: list[str],
        demoted_stages: list[str],
    ) -> Certification:
        """Update active_stages and record source='origin' events for auto-activated stages.

        Stages promoted to 'required' by a data_origin change are recorded with
        status='stage_added' and source='origin' so they don't count toward the
        RF-01f metric of poorly defined recipes.
        """
        cert.active_stages = new_stages
        now = datetime.now(UTC)
        for stage in promoted_stages:
            self._session.add(StageEvent(
                certification_id=cert.id,
                stage=stage,
                status="stage_added",
                source="origin",
                started_at=now,
            ))
        for stage in demoted_stages:
            self._session.add(StageEvent(
                certification_id=cert.id,
                stage=stage,
                status="stage_removed",
                source="origin",
                started_at=now,
            ))
        await self._session.commit()
        await self._session.refresh(cert)
        return cert

    async def stage_has_data(self, cert_id: uuid.UUID, stage: str) -> bool:
        """Return True if the stage already has rows in its associated table."""
        query = _STAGE_DATA_QUERIES.get(stage)
        if query is None:
            return False
        result = await self._session.execute(sa.text(query), {"cid": cert_id})
        return (result.scalar() or 0) > 0

    async def update_fields(self, cert: Certification, **kwargs: object) -> Certification:
        for key, value in kwargs.items():
            if value is not None:
                setattr(cert, key, value)
        await self._session.commit()
        await self._session.refresh(cert)
        return cert

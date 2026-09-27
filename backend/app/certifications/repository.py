import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.certifications.models import Certification, StageEvent


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
        description: Optional[str] = None,
    ) -> Certification:
        cert = Certification(
            owner_id=owner_id,
            type=type,
            external_code=external_code,
            module=module,
            title=title,
            description=description,
        )
        self._session.add(cert)
        await self._session.flush()  # genera cert.id y cert.stage antes del StageEvent
        event = StageEvent(certification_id=cert.id, stage=cert.stage)
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
        q = q.order_by(Certification.created_at.desc())
        result = await self._session.execute(q)
        return [(row.Certification, row.email) for row in result]

    async def update_stage(
        self, cert: Certification, new_stage: str
    ) -> Certification:
        # cerrar el event actual
        current_event = next(
            (e for e in cert.stage_events if e.stage == cert.stage and e.ended_at is None),
            None,
        )
        if current_event is not None:
            current_event.ended_at = datetime.now(UTC)

        cert.stage = new_stage
        if new_stage == "closed":
            cert.status = "closed"
            cert.closed_at = datetime.now(UTC)

        # abrir nuevo event
        new_event = StageEvent(certification_id=cert.id, stage=new_stage)
        self._session.add(new_event)
        await self._session.commit()
        await self._session.refresh(cert)
        return cert

    async def update_fields(
        self, cert: Certification, **kwargs: object
    ) -> Certification:
        for key, value in kwargs.items():
            if value is not None:
                setattr(cert, key, value)
        await self._session.commit()
        await self._session.refresh(cert)
        return cert

"""Tests unitarios de CertificationService usando un repositorio falso."""

import uuid
from datetime import datetime, UTC
from typing import Optional

import pytest

from app.certifications.models import Certification, STAGE_ORDER, StageEvent
from app.certifications.repository import CertificationRepository
from app.certifications.schemas import CertificationCreate, CertificationUpdate
from app.certifications.service import CertificationError, CertificationService


# â”€â”€ repositorio falso â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class _FakeCertRepo:
    def __init__(self) -> None:
        self._store: list[Certification] = []

    async def create(
        self,
        owner_id: uuid.UUID,
        type: str,
        external_code: str,
        module: str,
        title: str,
        description: Optional[str] = None,
    ) -> Certification:
        now = datetime.now(UTC)
        cert = Certification(
            id=uuid.uuid4(),
            owner_id=owner_id,
            type=type,
            external_code=external_code,
            module=module,
            title=title,
            description=description,
            stage="context",
            status="active",
            closed_at=None,
            created_at=now,
            updated_at=now,
        )
        cert.stage_events = [
            StageEvent(
                id=uuid.uuid4(),
                certification_id=cert.id,
                stage="context",
                started_at=now,
                ended_at=None,
            )
        ]
        self._store.append(cert)
        return cert

    async def get_by_id(
        self, cert_id: uuid.UUID, owner_id: Optional[uuid.UUID] = None
    ) -> Optional[Certification]:
        for c in self._store:
            if c.id == cert_id:
                if owner_id is None or c.owner_id == owner_id:
                    return c
        return None

    async def list_by_owner(
        self,
        owner_id: uuid.UUID,
        *,
        type: Optional[str] = None,
        module: Optional[str] = None,
        stage: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[Certification]:
        results = [c for c in self._store if c.owner_id == owner_id]
        if type:
            results = [c for c in results if c.type == type]
        if module:
            results = [c for c in results if c.module == module]
        if stage:
            results = [c for c in results if c.stage == stage]
        if status:
            results = [c for c in results if c.status == status]
        return results

    async def update_stage(self, cert: Certification, new_stage: str) -> Certification:
        now = datetime.now(UTC)
        for ev in cert.stage_events:
            if ev.stage == cert.stage and ev.ended_at is None:
                ev.ended_at = now
        cert.stage = new_stage
        if new_stage == "closed":
            cert.status = "closed"
            cert.closed_at = now
        cert.stage_events.append(
            StageEvent(
                id=uuid.uuid4(),
                certification_id=cert.id,
                stage=new_stage,
                started_at=now,
                ended_at=None,
            )
        )
        return cert

    async def update_fields(self, cert: Certification, **kwargs: object) -> Certification:
        for k, v in kwargs.items():
            setattr(cert, k, v)
        return cert


def _make_service() -> tuple[CertificationService, _FakeCertRepo]:
    repo = _FakeCertRepo()
    return CertificationService(repo), repo


_OWNER = uuid.uuid4()
_CREATE_DATA = CertificationCreate(
    type="brecha",
    external_code="BRE-001",
    module="Novedades de afiliacion",
    title="Exclusion de beneficiario",
)


# â”€â”€ create â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@pytest.mark.asyncio
async def test_create_returns_certification_in_first_stage() -> None:
    service, _ = _make_service()
    cert = await service.create(_OWNER, _CREATE_DATA)
    assert cert.stage == "context"
    assert cert.status == "active"
    assert cert.type == "brecha"


@pytest.mark.asyncio
async def test_create_opens_stage_event() -> None:
    service, _ = _make_service()
    cert = await service.create(_OWNER, _CREATE_DATA)
    assert len(cert.stage_events) == 1
    assert cert.stage_events[0].stage == "context"
    assert cert.stage_events[0].ended_at is None


@pytest.mark.asyncio
async def test_create_bug_type() -> None:
    service, _ = _make_service()
    bug_data = CertificationCreate(
        type="bug", external_code="IM-9142664", module="Novedades de afiliacion", title="Bug fix"
    )
    cert = await service.create(_OWNER, bug_data)
    assert cert.type == "bug"
    assert cert.external_code == "IM-9142664"


# â”€â”€ get â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@pytest.mark.asyncio
async def test_get_returns_own_certification() -> None:
    service, _ = _make_service()
    cert = await service.create(_OWNER, _CREATE_DATA)
    fetched = await service.get(cert.id, _OWNER)
    assert fetched.id == cert.id


@pytest.mark.asyncio
async def test_get_other_owner_raises() -> None:
    service, _ = _make_service()
    cert = await service.create(_OWNER, _CREATE_DATA)
    other = uuid.uuid4()
    with pytest.raises(CertificationError):
        await service.get(cert.id, other)


# â”€â”€ list â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@pytest.mark.asyncio
async def test_list_returns_only_owner_certifications() -> None:
    service, _ = _make_service()
    await service.create(_OWNER, _CREATE_DATA)
    await service.create(_OWNER, _CREATE_DATA)
    await service.create(uuid.uuid4(), _CREATE_DATA)  # otro owner
    results = await service.list(_OWNER)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_list_filters_by_type() -> None:
    service, _ = _make_service()
    await service.create(_OWNER, _CREATE_DATA)  # brecha
    bug_data = CertificationCreate(type="bug", external_code="B-1", module="M", title="T")
    await service.create(_OWNER, bug_data)
    bugs = await service.list(_OWNER, type="bug")
    assert len(bugs) == 1 and bugs[0].type == "bug"


# â”€â”€ change_stage â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@pytest.mark.asyncio
async def test_advance_stage_moves_forward() -> None:
    service, _ = _make_service()
    cert = await service.create(_OWNER, _CREATE_DATA)
    assert cert.stage == "context"
    cert = await service.change_stage(cert.id, _OWNER, "forward")
    assert cert.stage == "ambiguities"


@pytest.mark.asyncio
async def test_advance_stage_creates_new_event() -> None:
    service, _ = _make_service()
    cert = await service.create(_OWNER, _CREATE_DATA)
    cert = await service.change_stage(cert.id, _OWNER, "forward")
    stages = [e.stage for e in cert.stage_events]
    assert "context" in stages
    assert "ambiguities" in stages


@pytest.mark.asyncio
async def test_advance_stage_closes_previous_event() -> None:
    service, _ = _make_service()
    cert = await service.create(_OWNER, _CREATE_DATA)
    cert = await service.change_stage(cert.id, _OWNER, "forward")
    req_event = next(e for e in cert.stage_events if e.stage == "context")
    assert req_event.ended_at is not None


@pytest.mark.asyncio
async def test_go_back_stage_moves_backward() -> None:
    service, _ = _make_service()
    cert = await service.create(_OWNER, _CREATE_DATA)
    cert = await service.change_stage(cert.id, _OWNER, "forward")  # â†’ ambiguities
    cert = await service.change_stage(cert.id, _OWNER, "back")     # â†’ requirement
    assert cert.stage == "context"


@pytest.mark.asyncio
async def test_advance_from_last_stage_raises() -> None:
    service, _ = _make_service()
    cert = await service.create(_OWNER, _CREATE_DATA)
    # avanzar hasta closed
    for _ in range(len(STAGE_ORDER) - 1):
        cert = await service.change_stage(cert.id, _OWNER, "forward")
    assert cert.stage == "closed"
    with pytest.raises(CertificationError):
        await service.change_stage(cert.id, _OWNER, "forward")


@pytest.mark.asyncio
async def test_go_back_from_first_stage_raises() -> None:
    service, _ = _make_service()
    cert = await service.create(_OWNER, _CREATE_DATA)
    assert cert.stage == "context"
    with pytest.raises(CertificationError):
        await service.change_stage(cert.id, _OWNER, "back")


@pytest.mark.asyncio
async def test_closed_certification_sets_closed_at() -> None:
    service, _ = _make_service()
    cert = await service.create(_OWNER, _CREATE_DATA)
    for _ in range(len(STAGE_ORDER) - 1):
        cert = await service.change_stage(cert.id, _OWNER, "forward")
    assert cert.status == "closed"
    assert cert.closed_at is not None


# â”€â”€ update â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@pytest.mark.asyncio
async def test_update_changes_title() -> None:
    service, _ = _make_service()
    cert = await service.create(_OWNER, _CREATE_DATA)
    updated = await service.update(cert.id, _OWNER, CertificationUpdate(title="Nuevo tÃ­tulo"))
    assert updated.title == "Nuevo tÃ­tulo"

import uuid
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.certifications.repository import CertificationRepository
from app.certifications.schemas import (
    CertificationCreate,
    CertificationRead,
    CertificationUpdate,
    StageChangeRequest,
)
from app.certifications.service import CertificationError, CertificationService
from app.core.db import get_db
from app.users.models import User
from app.users.repository import UserRepository
from app.users.router import get_current_user
from app.users.service import AuthError, UserService

router = APIRouter(prefix="/api/v1/certifications", tags=["certifications"])


async def _current_user_id(
    access_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    try:
        user = await UserService(UserRepository(session)).get_by_token(access_token)
    except AuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")
    return user.id


def _service(session: AsyncSession = Depends(get_db)) -> CertificationService:
    return CertificationService(CertificationRepository(session))


@router.post("", response_model=CertificationRead, status_code=status.HTTP_201_CREATED)
async def create_certification(
    body: CertificationCreate,
    owner_id: uuid.UUID = Depends(_current_user_id),
    service: CertificationService = Depends(_service),
) -> CertificationRead:
    try:
        cert = await service.create(owner_id, body)
    except CertificationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return CertificationRead.model_validate(cert)


@router.get("", response_model=list[CertificationRead])
async def list_certifications(
    type: Optional[str] = Query(default=None),
    module: Optional[str] = Query(default=None),
    stage: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CertificationRead]:
    repo = CertificationRepository(session)
    if current_user.role in ("lead", "admin"):
        pairs = await repo.list_all_with_analyst_email(
            type=type, module=module, stage=stage, status=status_filter
        )
        return [
            CertificationRead.model_validate(cert).model_copy(update={"analyst_email": email})
            for cert, email in pairs
        ]
    certs = await repo.list_by_owner(
        current_user.id, type=type, module=module, stage=stage, status=status_filter
    )
    return [CertificationRead.model_validate(c) for c in certs]


@router.get("/{cert_id}", response_model=CertificationRead)
async def get_certification(
    cert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: CertificationService = Depends(_service),
) -> CertificationRead:
    # Admin y lead pueden ver cualquier certificación
    owner_id = None if current_user.role in ("admin", "lead") else current_user.id
    try:
        cert = await service.get(cert_id, owner_id)
    except CertificationError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return CertificationRead.model_validate(cert)


@router.patch("/{cert_id}", response_model=CertificationRead)
async def update_certification(
    cert_id: uuid.UUID,
    body: CertificationUpdate,
    current_user: User = Depends(get_current_user),
    service: CertificationService = Depends(_service),
) -> CertificationRead:
    owner_id = None if current_user.role in ("admin", "lead") else current_user.id
    try:
        cert = await service.update(cert_id, owner_id, body)
    except CertificationError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return CertificationRead.model_validate(cert)


@router.post("/{cert_id}/stage", response_model=CertificationRead)
async def change_stage(
    cert_id: uuid.UUID,
    body: StageChangeRequest,
    current_user: User = Depends(get_current_user),
    service: CertificationService = Depends(_service),
) -> CertificationRead:
    owner_id = None if current_user.role in ("admin", "lead") else current_user.id
    try:
        cert = await service.change_stage(cert_id, owner_id, body.direction)
    except CertificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if cert.stage == "closed":
        from app.knowledge.tasks import ingest_certification as knowledge_task
        knowledge_task.delay(str(cert_id), str(current_user.id))
    return CertificationRead.model_validate(cert)

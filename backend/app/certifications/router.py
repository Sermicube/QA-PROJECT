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
from app.users.repository import UserRepository
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
    owner_id: uuid.UUID = Depends(_current_user_id),
    service: CertificationService = Depends(_service),
) -> list[CertificationRead]:
    certs = await service.list(
        owner_id, type=type, module=module, stage=stage, status=status_filter
    )
    return [CertificationRead.model_validate(c) for c in certs]


@router.get("/{cert_id}", response_model=CertificationRead)
async def get_certification(
    cert_id: uuid.UUID,
    owner_id: uuid.UUID = Depends(_current_user_id),
    service: CertificationService = Depends(_service),
) -> CertificationRead:
    try:
        cert = await service.get(cert_id, owner_id)
    except CertificationError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return CertificationRead.model_validate(cert)


@router.patch("/{cert_id}", response_model=CertificationRead)
async def update_certification(
    cert_id: uuid.UUID,
    body: CertificationUpdate,
    owner_id: uuid.UUID = Depends(_current_user_id),
    service: CertificationService = Depends(_service),
) -> CertificationRead:
    try:
        cert = await service.update(cert_id, owner_id, body)
    except CertificationError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return CertificationRead.model_validate(cert)


@router.post("/{cert_id}/stage", response_model=CertificationRead)
async def change_stage(
    cert_id: uuid.UUID,
    body: StageChangeRequest,
    owner_id: uuid.UUID = Depends(_current_user_id),
    service: CertificationService = Depends(_service),
) -> CertificationRead:
    try:
        cert = await service.change_stage(cert_id, owner_id, body.direction)
    except CertificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    # RF-60: al cerrar, ingestar al Mapa Vivo en background
    if cert.stage == "closed":
        from app.knowledge.tasks import ingest_certification as knowledge_task
        knowledge_task.delay(str(cert_id), str(owner_id))
    return CertificationRead.model_validate(cert)

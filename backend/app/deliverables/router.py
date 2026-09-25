"""Endpoints del módulo deliverables (RF-40 a RF-44)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.deliverables.repository import DeliverableRepository
from app.deliverables.schemas import (
    DeliverableOut,
    DeliverableUpdateIn,
    GenerateDeliverablesOut,
    TemplateOut,
)
from app.deliverables.service import DeliverableError, DeliverableService
from app.users.models import User
from app.users.router import get_current_user

router = APIRouter(prefix="/api/v1", tags=["deliverables"])


def _svc(session: AsyncSession = Depends(get_session)) -> DeliverableService:
    return DeliverableService(DeliverableRepository(session))


def _repo(session: AsyncSession = Depends(get_session)) -> DeliverableRepository:
    return DeliverableRepository(session)


# ── Generar entregables (RF-40 a RF-43) ──────────────────────────────────────

@router.post(
    "/certifications/{cert_id}/deliverables/generate",
    response_model=GenerateDeliverablesOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_deliverables(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: DeliverableService = Depends(_svc),
) -> GenerateDeliverablesOut:
    task_id = await svc.generate_all(cert_id)
    return GenerateDeliverablesOut(task_id=task_id)


# ── Listar entregables ────────────────────────────────────────────────────────

@router.get("/certifications/{cert_id}/deliverables", response_model=list[DeliverableOut])
async def list_deliverables(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: DeliverableService = Depends(_svc),
) -> list[DeliverableOut]:
    items = await svc.get_deliverables(cert_id)
    return [DeliverableOut.model_validate(d) for d in items]


# ── Descargar entregable ──────────────────────────────────────────────────────

@router.get("/deliverables/{deliverable_id}/download")
async def download_deliverable(
    deliverable_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: DeliverableService = Depends(_svc),
) -> FileResponse:
    try:
        path = await svc.get_download_path(deliverable_id)
    except DeliverableError as e:
        raise HTTPException(status_code=404, detail=str(e))
    from pathlib import Path
    if not Path(path).exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en disco")
    return FileResponse(path=path, filename=Path(path).name)


# ── RF-44: editar contenido ───────────────────────────────────────────────────

@router.patch("/deliverables/{deliverable_id}", response_model=DeliverableOut)
async def update_deliverable(
    deliverable_id: uuid.UUID,
    body: DeliverableUpdateIn,
    _user: User = Depends(get_current_user),
    svc: DeliverableService = Depends(_svc),
) -> DeliverableOut:
    try:
        d = await svc.update_content(deliverable_id, body.content)
    except DeliverableError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return DeliverableOut.model_validate(d)


# ── Plantillas CO-FR-VRA-03 ───────────────────────────────────────────────────

@router.post(
    "/templates",
    response_model=TemplateOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_template(
    kind: str,
    name: str,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    repo: DeliverableRepository = Depends(_repo),
) -> TemplateOut:
    from app.core.storage import save_upload
    import uuid as _uuid
    data = await file.read()
    # Guardar en directorio especial de plantillas
    from pathlib import Path
    from app.core.config import settings
    tmpl_dir = Path(settings.FILES_DIR) / "templates"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{_uuid.uuid4().hex}_{file.filename}"
    dest = tmpl_dir / stored_name
    dest.write_bytes(data)
    t = await repo.create_template(
        kind=kind,
        name=name,
        file_path=str(dest),
        mapping={},
        owner_id=current_user.id,
    )
    return TemplateOut.model_validate(t)


@router.get("/templates", response_model=list[TemplateOut])
async def list_templates(
    kind: str | None = None,
    _user: User = Depends(get_current_user),
    repo: DeliverableRepository = Depends(_repo),
) -> list[TemplateOut]:
    templates = await repo.list_templates(kind)
    return [TemplateOut.model_validate(t) for t in templates]

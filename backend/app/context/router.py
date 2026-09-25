"""Endpoints del módulo context (RF-10 a RF-14)."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.repository import ContextRepository
from app.context.schemas import (
    AmbiguityOut,
    AmbiguityResolve,
    AnalyzeOut,
    ContextSourceOut,
    CriterionOut,
    DescriptionIn,
    IncidentReportIn,
)
from app.context.service import ContextError, ContextService
from app.core.config import settings
from app.core.db import get_session
from app.users.models import User
from app.users.router import get_current_user

router = APIRouter(prefix="/api/v1", tags=["context"])


def _svc(session: AsyncSession = Depends(get_session)) -> ContextService:
    return ContextService(ContextRepository(session))


# ── Listar fuentes ────────────────────────────────────────────────────────────

@router.get(
    "/certifications/{cert_id}/context",
    response_model=list[ContextSourceOut],
)
async def list_context(
    cert_id: uuid.UUID,
    svc: ContextService = Depends(_svc),
    _user: User = Depends(get_current_user),
) -> list[ContextSourceOut]:
    sources = await svc.get_sources(cert_id)
    return [ContextSourceOut.model_validate(s) for s in sources]


# ── Descripción del analista (RF-10a) ─────────────────────────────────────────

@router.put(
    "/certifications/{cert_id}/context/description",
    response_model=ContextSourceOut,
    status_code=status.HTTP_200_OK,
)
async def save_description(
    cert_id: uuid.UUID,
    body: DescriptionIn,
    user: User = Depends(get_current_user),
    svc: ContextService = Depends(_svc),
) -> ContextSourceOut:
    try:
        source = await svc.save_description(cert_id, user.role, body.content)
    except ContextError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ContextSourceOut.model_validate(source)


# ── Documento de requerimiento (RF-10b) ───────────────────────────────────────

@router.post(
    "/certifications/{cert_id}/context/document",
    response_model=ContextSourceOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    cert_id: uuid.UUID,
    file: UploadFile,
    _user: User = Depends(get_current_user),
    svc: ContextService = Depends(_svc),
) -> ContextSourceOut:
    allowed = {".docx", ".pdf"}
    import os
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido. Usar: {allowed}")

    data = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"El archivo supera el límite de {settings.MAX_UPLOAD_MB} MB")

    try:
        source = await svc.save_document(
            cert_id,
            file_name=file.filename or "document",
            mime_type=file.content_type or "application/octet-stream",
            data=data,
        )
    except ContextError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ContextSourceOut.model_validate(source)


# ── Reporte del incidente (RF-10c) ─────────────────────────────────────────────

@router.put(
    "/certifications/{cert_id}/context/incident-report",
    response_model=ContextSourceOut,
)
async def save_incident_report(
    cert_id: uuid.UUID,
    body: IncidentReportIn,
    _user: User = Depends(get_current_user),
    svc: ContextService = Depends(_svc),
) -> ContextSourceOut:
    source = await svc.save_incident_report(cert_id, body.text)
    return ContextSourceOut.model_validate(source)


# ── Eliminar fuente ────────────────────────────────────────────────────────────

@router.delete(
    "/context-sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_source(
    source_id: uuid.UUID,
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: ContextService = Depends(_svc),
) -> None:
    try:
        await svc.delete_source(cert_id, source_id)
    except ContextError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Completitud (RF-10d) ───────────────────────────────────────────────────────

@router.post("/certifications/{cert_id}/context/completeness")
async def check_completeness(
    cert_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: ContextService = Depends(_svc),
) -> list[dict]:
    return await svc.check_completeness(cert_id, user.role)


# ── Analizar contexto (RF-12, RF-13) ──────────────────────────────────────────

@router.post(
    "/certifications/{cert_id}/context/analyze",
    response_model=AnalyzeOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_context(
    cert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: ContextService = Depends(_svc),
) -> AnalyzeOut:
    # Primero correr análisis local (rápido, sin LLM)
    await svc.run_local_ambiguity_scan(cert_id)
    # Lanzar tarea Celery para análisis LLM
    from app.context.tasks import analyze_context as celery_task
    task = celery_task.delay(str(cert_id), str(current_user.id))
    return AnalyzeOut(task_id=task.id)


# ── Criterios (RF-12) ─────────────────────────────────────────────────────────

@router.get("/certifications/{cert_id}/criteria", response_model=list[CriterionOut])
async def list_criteria(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: ContextService = Depends(_svc),
) -> list[CriterionOut]:
    return [CriterionOut.model_validate(c) for c in await svc.get_criteria(cert_id)]


# ── Ambigüedades (RF-13, RF-14) ───────────────────────────────────────────────

@router.get("/certifications/{cert_id}/ambiguities", response_model=list[AmbiguityOut])
async def list_ambiguities(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: ContextService = Depends(_svc),
) -> list[AmbiguityOut]:
    return [AmbiguityOut.model_validate(a) for a in await svc.get_ambiguities(cert_id)]


@router.patch("/ambiguities/{amb_id}", response_model=AmbiguityOut)
async def resolve_ambiguity(
    amb_id: uuid.UUID,
    body: AmbiguityResolve,
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: ContextService = Depends(_svc),
) -> AmbiguityOut:
    try:
        amb = await svc.resolve_ambiguity(cert_id, amb_id, body.resolution, body.resolved_by)
    except ContextError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return AmbiguityOut.model_validate(amb)

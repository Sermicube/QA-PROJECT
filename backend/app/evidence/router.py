"""Endpoints del módulo evidence (RF-31 a RF-34)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.evidence.repository import EvidenceRepository
from app.evidence.schemas import AcceptWarningIn, EvidenceOut, ExecutionIn, ExecutionOut, OcrTaskOut
from app.evidence.service import EvidenceError, EvidenceService
from app.users.models import User
from app.users.router import get_current_user

router = APIRouter(prefix="/api/v1", tags=["evidence"])


def _svc(session: AsyncSession = Depends(get_session)) -> EvidenceService:
    return EvidenceService(EvidenceRepository(session))


def _repo(session: AsyncSession = Depends(get_session)) -> EvidenceRepository:
    return EvidenceRepository(session)


# ── RF-31: subir pantallazo ────────────────────────────────────────────────────

@router.post(
    "/testcases/{tc_id}/evidence",
    response_model=OcrTaskOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_evidence(
    tc_id: uuid.UUID,
    cert_id: uuid.UUID,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    svc: EvidenceService = Depends(_svc),
) -> OcrTaskOut:
    data = await file.read()
    try:
        ev = await svc.upload_screenshot(
            tc_id=tc_id,
            cert_id=cert_id,
            file_name=file.filename or "screenshot.png",
            mime_type=file.content_type or "image/png",
            data=data,
        )
    except EvidenceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    from app.evidence.tasks import validate_ocr as ocr_task
    task = ocr_task.delay(str(ev.id))
    return OcrTaskOut(task_id=task.id, evidence_id=ev.id)


# ── Listar evidencias ─────────────────────────────────────────────────────────

@router.get("/testcases/{tc_id}/evidence", response_model=list[EvidenceOut])
async def list_evidence(
    tc_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    repo: EvidenceRepository = Depends(_repo),
) -> list[EvidenceOut]:
    evs = await repo.list_by_case(tc_id)
    return [EvidenceOut.model_validate(e) for e in evs]


# ── RF-32 + RF-34: aceptar advertencia / editar caption ───────────────────────

@router.patch("/evidence/{evidence_id}", response_model=EvidenceOut)
async def patch_evidence(
    evidence_id: uuid.UUID,
    body: AcceptWarningIn,
    _user: User = Depends(get_current_user),
    svc: EvidenceService = Depends(_svc),
) -> EvidenceOut:
    try:
        ev = await svc.accept_warning(evidence_id, body.reason)
        if body.caption:
            ev = await svc._repo.update_caption(evidence_id, body.caption)
    except (EvidenceError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return EvidenceOut.model_validate(ev)


# ── RF-34: generar caption automático ─────────────────────────────────────────

@router.post("/evidence/{evidence_id}/caption", response_model=EvidenceOut)
async def generate_caption(
    evidence_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: EvidenceService = Depends(_svc),
) -> EvidenceOut:
    try:
        ev = await svc.generate_caption(evidence_id)
    except (EvidenceError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return EvidenceOut.model_validate(ev)


# ── RF-33: registrar resultado de ejecución ───────────────────────────────────

@router.put("/testcases/{tc_id}/execution", response_model=ExecutionOut)
async def record_execution(
    tc_id: uuid.UUID,
    body: ExecutionIn,
    _user: User = Depends(get_current_user),
    svc: EvidenceService = Depends(_svc),
) -> ExecutionOut:
    try:
        ex = await svc.record_execution(tc_id, body.result, body.observation)
    except EvidenceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ExecutionOut.model_validate(ex)


@router.get("/testcases/{tc_id}/execution", response_model=ExecutionOut)
async def get_execution(
    tc_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    repo: EvidenceRepository = Depends(_repo),
) -> ExecutionOut:
    ex = await repo.get_execution(tc_id)
    if ex is None:
        raise HTTPException(status_code=404, detail="Sin resultado registrado para este caso")
    return ExecutionOut.model_validate(ex)


@router.get("/certifications/{cert_id}/executions", response_model=list[ExecutionOut])
async def list_executions(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    repo: EvidenceRepository = Depends(_repo),
) -> list[ExecutionOut]:
    execs = await repo.list_executions(cert_id)
    return [ExecutionOut.model_validate(e) for e in execs]

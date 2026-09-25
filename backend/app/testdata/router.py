"""Endpoints del módulo testdata (RF-20 a RF-29)."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.testdata.repository import TestDataRepository
from app.testdata.schemas import (
    AssignmentOut,
    CaseConditionsIn,
    CaseConditionsOut,
    ColumnMappingOut,
    DataRequestOut,
    DomainFieldOut,
    MappingConfirmIn,
    MappingSuggestOut,
    SuggestConditionsOut,
    UserBaseOut,
    UserBasePreview,
)
from app.testdata.service import TestDataError, TestDataService
from app.users.models import User
from app.users.router import get_current_user

router = APIRouter(prefix="/api/v1", tags=["testdata"])


def _svc(session: AsyncSession = Depends(get_session)) -> TestDataService:
    return TestDataService(TestDataRepository(session))


def _repo(session: AsyncSession = Depends(get_session)) -> TestDataRepository:
    return TestDataRepository(session)


# ── Subir base (RF-20) ────────────────────────────────────────────────────────

@router.post(
    "/certifications/{cert_id}/userbase",
    response_model=UserBaseOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_userbase(
    cert_id: uuid.UUID,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    svc: TestDataService = Depends(_svc),
) -> UserBaseOut:
    data = await file.read()
    try:
        base = await svc.upload_base(
            cert_id=cert_id,
            file_name=file.filename or "base.txt",
            mime_type=file.content_type or "text/plain",
            data=data,
            owner_id=current_user.id,
        )
    except TestDataError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserBaseOut.model_validate(base)


# ── Vista previa (RF-21) ──────────────────────────────────────────────────────

@router.get("/userbases/{base_id}/preview", response_model=UserBasePreview)
async def preview_base(
    base_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: TestDataService = Depends(_svc),
) -> UserBasePreview:
    try:
        return await svc.preview_base(base_id)
    except TestDataError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Mapeo local (RF-22) ───────────────────────────────────────────────────────

@router.post("/userbases/{base_id}/mapping/suggest", response_model=MappingSuggestOut)
async def suggest_mapping(
    base_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: TestDataService = Depends(_svc),
    repo: TestDataRepository = Depends(_repo),
) -> MappingSuggestOut:
    try:
        suggestions = await svc.suggest_mapping_local(base_id)
        base = await repo.get_base(base_id)
        fingerprint = base.header_fingerprint if base else ""
    except TestDataError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return MappingSuggestOut(suggestions=suggestions, fingerprint=fingerprint)


@router.put("/userbases/{base_id}/mapping", response_model=ColumnMappingOut)
async def confirm_mapping(
    base_id: uuid.UUID,
    body: MappingConfirmIn,
    current_user: User = Depends(get_current_user),
    svc: TestDataService = Depends(_svc),
) -> ColumnMappingOut:
    try:
        cm = await svc.confirm_mapping(
            base_id=base_id,
            owner_id=current_user.id,
            module=body.module,
            mapping_dict=body.mapping,
        )
    except TestDataError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ColumnMappingOut.model_validate(cm)


# ── Condiciones (RF-23) ───────────────────────────────────────────────────────

@router.post(
    "/testcases/{tc_id}/conditions/suggest",
    response_model=SuggestConditionsOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def suggest_conditions(
    tc_id: uuid.UUID,
    _user: User = Depends(get_current_user),
) -> SuggestConditionsOut:
    from app.testdata.tasks import suggest_conditions as celery_task
    task = celery_task.delay(str(tc_id))
    return SuggestConditionsOut(task_id=task.id)


@router.put("/testcases/{tc_id}/conditions", response_model=CaseConditionsOut)
async def set_conditions(
    tc_id: uuid.UUID,
    body: CaseConditionsIn,
    _user: User = Depends(get_current_user),
    repo: TestDataRepository = Depends(_repo),
) -> CaseConditionsOut:
    cc = await repo.upsert_conditions(
        tc_id=tc_id,
        conditions=body.conditions,
        derived_inputs=body.derived_inputs,
        mutates_state=body.mutates_state,
    )
    cc = await repo.confirm_conditions(tc_id)
    return CaseConditionsOut.model_validate(cc)


@router.get("/testcases/{tc_id}/conditions", response_model=CaseConditionsOut)
async def get_conditions(
    tc_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    repo: TestDataRepository = Depends(_repo),
) -> CaseConditionsOut:
    cc = await repo.get_conditions(tc_id)
    if cc is None:
        raise HTTPException(status_code=404, detail="Sin condiciones para este caso")
    return CaseConditionsOut.model_validate(cc)


# ── Asignación (RF-24+25+26+27+28) ───────────────────────────────────────────

@router.post("/certifications/{cert_id}/assign", response_model=list[AssignmentOut])
async def run_assignment(
    cert_id: uuid.UUID,
    base_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: TestDataService = Depends(_svc),
) -> list[AssignmentOut]:
    try:
        return await svc.run_assignment(cert_id, base_id)
    except TestDataError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/certifications/{cert_id}/assignments", response_model=list[AssignmentOut])
async def list_assignments(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    repo: TestDataRepository = Depends(_repo),
) -> list[AssignmentOut]:
    assignments = await repo.list_assignments(cert_id)
    return [AssignmentOut.model_validate(a) for a in assignments]


# ── Reemplazar usuario (RF-29) ────────────────────────────────────────────────

@router.patch("/assignments/{assignment_id}", response_model=AssignmentOut)
async def override_assignment(
    assignment_id: uuid.UUID,
    new_row_ref: int,
    _user: User = Depends(get_current_user),
    svc: TestDataService = Depends(_svc),
) -> AssignmentOut:
    try:
        a = await svc.override_assignment(assignment_id, new_row_ref)
    except (TestDataError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    return AssignmentOut.model_validate(a)


# ── Solicitudes de datos (RF-28) ──────────────────────────────────────────────

@router.get("/certifications/{cert_id}/data-requests", response_model=list[DataRequestOut])
async def list_data_requests(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    repo: TestDataRepository = Depends(_repo),
) -> list[DataRequestOut]:
    reqs = await repo.list_data_requests(cert_id)
    return [DataRequestOut.model_validate(r) for r in reqs]


# ── Campos de dominio ─────────────────────────────────────────────────────────

@router.get("/domain-fields", response_model=list[DomainFieldOut])
async def list_domain_fields(
    module: str | None = None,
    _user: User = Depends(get_current_user),
    repo: TestDataRepository = Depends(_repo),
) -> list[DomainFieldOut]:
    fields = await repo.list_domain_fields(module)
    return [DomainFieldOut.model_validate(f) for f in fields]

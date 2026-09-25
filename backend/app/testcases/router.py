"""Endpoints del módulo testcases (RF-15 a RF-19)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.repository import ContextRepository
from app.core.db import get_session
from app.testcases.repository import TestCaseRepository
from app.testcases.schemas import (
    GenerateOut,
    ImportCasesIn,
    LintIssueOut,
    TestCaseCreate,
    TestCaseOut,
    TestCaseUpdate,
    TraceabilityRow,
)
from app.testcases.service import TestCaseError, TestCaseService
from app.users.models import User
from app.users.router import get_current_user

router = APIRouter(prefix="/api/v1", tags=["testcases"])


def _svc(session: AsyncSession = Depends(get_session)) -> TestCaseService:
    return TestCaseService(TestCaseRepository(session), ContextRepository(session))


def _tc_out(tc: object) -> TestCaseOut:
    """Construye TestCaseOut inyectando criteria_ids desde criteria_links."""
    from app.testcases.models import TestCase
    assert isinstance(tc, TestCase)
    out = TestCaseOut.model_validate(tc)
    out.criteria_ids = [str(link.criterion_id) for link in (tc.criteria_links or [])]
    return out


# ── CRUD ───────────────────────────────────────────────────────────────────────

@router.get("/certifications/{cert_id}/testcases", response_model=list[TestCaseOut])
async def list_testcases(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: TestCaseService = Depends(_svc),
) -> list[TestCaseOut]:
    cases = await svc.list(cert_id)
    return [_tc_out(tc) for tc in cases]


@router.post(
    "/certifications/{cert_id}/testcases",
    response_model=TestCaseOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_testcase(
    cert_id: uuid.UUID,
    body: TestCaseCreate,
    _user: User = Depends(get_current_user),
    svc: TestCaseService = Depends(_svc),
) -> TestCaseOut:
    tc = await svc.create(
        certification_id=cert_id,
        name=body.name,
        preconditions=body.preconditions,
        steps=body.steps,
        expected_result=body.expected_result,
        criteria_ids=body.criteria_ids,
        boundary=body.boundary,
        order=body.order,
    )
    return _tc_out(tc)


@router.get("/testcases/{tc_id}", response_model=TestCaseOut)
async def get_testcase(
    tc_id: uuid.UUID,
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: TestCaseService = Depends(_svc),
) -> TestCaseOut:
    try:
        tc = await svc.get(tc_id, cert_id)
    except TestCaseError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _tc_out(tc)


@router.patch("/testcases/{tc_id}", response_model=TestCaseOut)
async def update_testcase(
    tc_id: uuid.UUID,
    cert_id: uuid.UUID,
    body: TestCaseUpdate,
    _user: User = Depends(get_current_user),
    svc: TestCaseService = Depends(_svc),
) -> TestCaseOut:
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        tc = await svc.update(tc_id, cert_id, **updates)
    except TestCaseError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _tc_out(tc)


@router.delete("/testcases/{tc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_testcase(
    tc_id: uuid.UUID,
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: TestCaseService = Depends(_svc),
) -> None:
    try:
        await svc.delete(tc_id, cert_id)
    except TestCaseError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Linter (RF-17) ─────────────────────────────────────────────────────────────

@router.post("/testcases/{tc_id}/lint", response_model=list[LintIssueOut])
async def lint_testcase(
    tc_id: uuid.UUID,
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: TestCaseService = Depends(_svc),
) -> list[LintIssueOut]:
    try:
        issues = await svc.lint(tc_id, cert_id)
    except TestCaseError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return [LintIssueOut(code=i.code, message=i.message, severity=i.severity) for i in issues]


@router.post("/certifications/{cert_id}/testcases/lint-all", response_model=dict)
async def lint_all(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: TestCaseService = Depends(_svc),
) -> dict:
    results = await svc.lint_all(cert_id)
    return {
        code: [{"code": i.code, "message": i.message, "severity": i.severity} for i in issues]
        for code, issues in results.items()
    }


# ── Aprobar (RF-18) ────────────────────────────────────────────────────────────

@router.post("/testcases/{tc_id}/approve", response_model=TestCaseOut)
async def approve_testcase(
    tc_id: uuid.UUID,
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: TestCaseService = Depends(_svc),
) -> TestCaseOut:
    try:
        tc = await svc.approve(tc_id, cert_id)
    except TestCaseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _tc_out(tc)


# ── Importar (RF-16) ──────────────────────────────────────────────────────────

@router.post(
    "/certifications/{cert_id}/testcases/import",
    response_model=list[TestCaseOut],
    status_code=status.HTTP_201_CREATED,
)
async def import_testcases(
    cert_id: uuid.UUID,
    body: ImportCasesIn,
    _user: User = Depends(get_current_user),
    svc: TestCaseService = Depends(_svc),
) -> list[TestCaseOut]:
    cases = await svc.import_cases(cert_id, [c.model_dump() for c in body.cases])
    return [_tc_out(tc) for tc in cases]


# ── Generar vía LLM (RF-15) ────────────────────────────────────────────────────

@router.post(
    "/certifications/{cert_id}/testcases/generate",
    response_model=GenerateOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_testcases(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
) -> GenerateOut:
    from app.testcases.tasks import generate_cases as celery_task
    task = celery_task.delay(str(cert_id))
    return GenerateOut(task_id=task.id)


# ── Matriz de trazabilidad (RF-19) ─────────────────────────────────────────────

@router.get("/certifications/{cert_id}/traceability", response_model=list[TraceabilityRow])
async def traceability(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: TestCaseService = Depends(_svc),
) -> list[TraceabilityRow]:
    return await svc.traceability(cert_id)

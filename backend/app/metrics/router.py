"""Endpoints del módulo metrics (RF-50 a RF-52)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.metrics.repository import MetricsRepository
from app.metrics.schemas import (
    BaselineCertificationIn,
    BaselineCertificationOut,
    MetricsSummaryOut,
    ReworkEventIn,
    ReworkEventOut,
)
from app.metrics.service import MetricsService
from app.users.models import User
from app.users.router import get_current_user

router = APIRouter(prefix="/api/v1", tags=["metrics"])


def _svc(session: AsyncSession = Depends(get_session)) -> MetricsService:
    return MetricsService(MetricsRepository(session))


# ── RF-51: devoluciones ───────────────────────────────────────────────────────

@router.post("/metrics/rework", response_model=ReworkEventOut, status_code=201)
async def add_rework(
    body: ReworkEventIn,
    _user: User = Depends(get_current_user),
    svc: MetricsService = Depends(_svc),
) -> ReworkEventOut:
    ev = await svc.add_rework(body.certification_id, body.test_case_id, body.reason)
    return ReworkEventOut.model_validate(ev)


@router.get("/metrics/rework/{cert_id}", response_model=list[ReworkEventOut])
async def list_rework(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: MetricsService = Depends(_svc),
) -> list[ReworkEventOut]:
    events = await svc.list_rework(cert_id)
    return [ReworkEventOut.model_validate(e) for e in events]


# ── RF-52: línea base ─────────────────────────────────────────────────────────

@router.post("/metrics/baseline", response_model=BaselineCertificationOut, status_code=201)
async def add_baseline(
    body: BaselineCertificationIn,
    current_user: User = Depends(get_current_user),
    svc: MetricsService = Depends(_svc),
) -> BaselineCertificationOut:
    b = await svc.add_baseline(
        owner_id=current_user.id,
        type=body.type,
        module=body.module,
        duration_minutes=body.duration_minutes,
        cert_date=body.date,
        notes=body.notes,
    )
    return BaselineCertificationOut.model_validate(b)


@router.get("/metrics/baseline", response_model=list[BaselineCertificationOut])
async def list_baselines(
    current_user: User = Depends(get_current_user),
    svc: MetricsService = Depends(_svc),
) -> list[BaselineCertificationOut]:
    items = await svc.list_baselines(current_user.id)
    return [BaselineCertificationOut.model_validate(b) for b in items]


# ── RF-50: resumen ────────────────────────────────────────────────────────────

@router.get("/metrics/summary", response_model=MetricsSummaryOut)
async def metrics_summary(
    current_user: User = Depends(get_current_user),
    svc: MetricsService = Depends(_svc),
) -> MetricsSummaryOut:
    return await svc.summary(current_user.id)

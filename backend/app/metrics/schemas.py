"""Schemas Pydantic del módulo metrics."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class ReworkEventIn(BaseModel):
    certification_id: uuid.UUID
    test_case_id: uuid.UUID | None = None
    reason: str


class ReworkEventOut(BaseModel):
    id: uuid.UUID
    certification_id: uuid.UUID
    test_case_id: uuid.UUID | None
    reason: str
    reported_at: datetime

    model_config = {"from_attributes": True}


class BaselineCertificationIn(BaseModel):
    type: str
    module: str
    duration_minutes: int
    date: date
    notes: str | None = None


class BaselineCertificationOut(BaseModel):
    id: uuid.UUID
    type: str
    module: str
    duration_minutes: int
    date: date
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ModuleMetrics(BaseModel):
    type: str
    module: str
    avg_duration_minutes: float | None
    baseline_avg_minutes: float | None
    total_certifications: int
    total_rework: int


class MetricsSummaryOut(BaseModel):
    by_module: list[ModuleMetrics]
    total_certifications: int
    total_rework: int
    overall_avg_minutes: float | None
    baseline_avg_minutes: float | None

"""Schemas Pydantic del módulo evidence."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class EvidenceOut(BaseModel):
    id: uuid.UUID
    test_case_id: uuid.UUID
    file_name: str
    mime_type: str
    ocr_status: str
    ocr_time_found: bool
    ocr_url_found: bool
    ocr_time_value: str | None
    ocr_url_value: str | None
    accepted_with_reason: str | None
    caption: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AcceptWarningIn(BaseModel):
    reason: str
    caption: str | None = None


class ExecutionIn(BaseModel):
    result: str  # passed | failed | blocked
    observation: str | None = None


class ExecutionOut(BaseModel):
    id: uuid.UUID
    test_case_id: uuid.UUID
    result: str
    observation: str | None
    executed_at: datetime

    model_config = {"from_attributes": True}


class OcrTaskOut(BaseModel):
    task_id: str
    evidence_id: uuid.UUID

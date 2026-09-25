import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Fuentes de contexto ──────────────────────────────────────────────────────

class BugDescriptionContent(BaseModel):
    bug_behavior: Optional[str] = None
    cause: Optional[str] = None
    fix: Optional[str] = None
    what_to_test: str
    expected_result: Optional[str] = None
    out_of_scope: Optional[str] = None
    free_text: Optional[str] = None


class BrechaDescriptionContent(BaseModel):
    what_changes: Optional[str] = None
    what_to_test: str
    expected_result: Optional[str] = None
    out_of_scope: Optional[str] = None
    free_text: Optional[str] = None


class DescriptionIn(BaseModel):
    content: dict[str, Any]  # BugDescriptionContent o BrechaDescriptionContent


class IncidentReportIn(BaseModel):
    text: str = Field(..., min_length=10)


class SectionOut(BaseModel):
    title: str
    content: str
    level: int


class CompletenessFindingOut(BaseModel):
    id: uuid.UUID
    field: str
    message: str
    dismissed: bool


class ContextSourceOut(BaseModel):
    id: uuid.UUID
    certification_id: uuid.UUID
    kind: str
    content: Optional[dict[str, Any]]
    file_name: Optional[str]
    mime_type: Optional[str]
    extracted_text: Optional[str]
    sections: Optional[list[SectionOut]]
    completeness_findings: list[CompletenessFindingOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Criterios ────────────────────────────────────────────────────────────────

class CriterionOut(BaseModel):
    id: uuid.UUID
    certification_id: uuid.UUID
    code: str
    text: str
    source_kind: str
    source_section: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Ambigüedades ─────────────────────────────────────────────────────────────

class AmbiguityOut(BaseModel):
    id: uuid.UUID
    certification_id: uuid.UUID
    type: str
    fragment: str
    location: str
    explanation: str
    question: str
    resolution: Optional[str]
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class AmbiguityResolve(BaseModel):
    resolution: str = Field(..., min_length=5)
    resolved_by: str = Field(..., min_length=2)


# ── Análisis (tarea async) ───────────────────────────────────────────────────

class AnalyzeOut(BaseModel):
    task_id: str

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LintIssueOut(BaseModel):
    code: str
    message: str
    severity: str


class TestCaseCreate(BaseModel):
    name: str = Field(..., min_length=10, max_length=300)
    criteria_ids: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    expected_result: str = Field(..., min_length=5)
    boundary: Optional[str] = None
    order: int = 0


class TestCaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=10, max_length=300)
    preconditions: Optional[list[str]] = None
    steps: Optional[list[str]] = None
    expected_result: Optional[str] = None
    boundary: Optional[str] = None
    criteria_ids: Optional[list[str]] = None
    order: Optional[int] = None


class TestCaseOut(BaseModel):
    id: uuid.UUID
    certification_id: uuid.UUID
    code: str
    name: str
    preconditions: list[str]
    steps: list[str]
    expected_result: str
    boundary: Optional[str]
    status: str
    lint_results: Optional[list[LintIssueOut]]
    criteria_ids: list[str] = Field(default_factory=list)
    order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImportCasesIn(BaseModel):
    cases: list[TestCaseCreate]


class GenerateOut(BaseModel):
    task_id: str


class TraceabilityRow(BaseModel):
    criterion_code: str
    criterion_text: str
    case_codes: list[str]
    covered: bool

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RecipeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    description: str
    stages: dict[str, str]
    default_case_style: str
    default_evidence_style: str
    default_execution_channel: str
    default_data_origin: str
    suggested_case_pattern: str
    is_builtin: bool
    created_at: datetime
    updated_at: datetime


class CaseStyleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    fields: dict
    lint_rules: dict
    example: str


class CasePatternRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    description: str
    n_cases_typical: Optional[str] = None
    notes: str


class InconclusiveReasonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    label: str
    description: str
    is_active: bool


class InconclusiveReasonToggle(BaseModel):
    is_active: bool

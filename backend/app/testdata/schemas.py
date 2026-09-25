"""Schemas Pydantic del módulo testdata."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DomainFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    label: str
    data_type: str
    module: str
    synonyms: list[str]


class ColumnMappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    header_fingerprint: str
    mapping: dict[str, str | None]
    module: str
    is_global: bool


class ColumnMappingCreate(BaseModel):
    module: str
    mapping: dict[str, str | None]


class UserBaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    certification_id: uuid.UUID
    file_name: str
    header_fingerprint: str
    row_count: int
    mapping_id: uuid.UUID | None
    purge_after: datetime


class UserBasePreview(BaseModel):
    id: uuid.UUID
    file_name: str
    row_count: int
    headers: list[str]
    types: dict[str, str]
    rows: list[dict[str, str]]


class MappingSuggestOut(BaseModel):
    suggestions: dict[str, str | None]
    fingerprint: str


class MappingConfirmIn(BaseModel):
    module: str
    mapping: dict[str, str | None]


class CaseConditionsIn(BaseModel):
    conditions: list[dict[str, Any]]
    derived_inputs: list[dict[str, Any]] = []
    mutates_state: bool = True


class CaseConditionsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    test_case_id: uuid.UUID
    conditions: list[dict[str, Any]]
    derived_inputs: list[dict[str, Any]]
    mutates_state: bool
    confirmed: bool


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    test_case_id: uuid.UUID
    user_base_id: uuid.UUID
    row_ref: int
    rank: int
    cost: float
    justification: dict[str, Any]
    derived_values: dict[str, Any]
    manual_override: bool


class DataRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    certification_id: uuid.UUID
    test_case_id: uuid.UUID
    text: str


class SuggestConditionsOut(BaseModel):
    task_id: str

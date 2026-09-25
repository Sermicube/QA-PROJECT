"""Schemas Pydantic del módulo deliverables."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class DeliverableOut(BaseModel):
    id: uuid.UUID
    certification_id: uuid.UUID
    kind: str
    file_path: str | None
    content: str | None
    generated_at: datetime

    model_config = {"from_attributes": True}


class DeliverableUpdateIn(BaseModel):
    content: str


class TemplateOut(BaseModel):
    id: uuid.UUID
    kind: str
    name: str
    is_global: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateDeliverablesOut(BaseModel):
    task_id: str

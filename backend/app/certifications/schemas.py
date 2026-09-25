import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


CertType = Literal["bug", "brecha"]
Stage = Literal[
    "requirement", "ambiguities", "testcases", "testdata", "execution", "deliverables", "closed"
]


class CertificationCreate(BaseModel):
    type: CertType
    external_code: str
    module: str
    title: str
    description: Optional[str] = None


class CertificationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    module: Optional[str] = None


class StageEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    stage: str
    started_at: datetime
    ended_at: Optional[datetime] = None


class CertificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    owner_id: uuid.UUID
    type: str
    external_code: str
    module: str
    title: str
    description: Optional[str] = None
    stage: str
    status: str
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    stage_events: list[StageEventRead] = []


class StageChangeRequest(BaseModel):
    direction: Literal["forward", "back"]

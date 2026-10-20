import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


CertType = Literal["bug", "brecha"]


class CertificationCreate(BaseModel):
    type: CertType
    external_code: str
    module: str
    title: str
    description: Optional[str] = None
    service: Optional[str] = None
    recipe_code: str = "bug_simple"   # default; overridden by frontend selector
    # analyst can override recipe defaults
    case_style: Optional[str] = None
    evidence_style: Optional[str] = None
    execution_channel: Optional[str] = None
    data_origin: Optional[str] = None


class CertificationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    module: Optional[str] = None
    service: Optional[str] = None
    case_style: Optional[str] = None
    evidence_style: Optional[str] = None
    execution_channel: Optional[str] = None
    data_origin: Optional[str] = None


class StageEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    stage: str
    status: Optional[str] = None
    source: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None


class CertificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    owner_id: uuid.UUID
    type: str
    external_code: str
    module: str
    service: Optional[str] = None
    title: str
    description: Optional[str] = None
    recipe_code: Optional[str] = None
    active_stages: Optional[dict[str, str]] = None
    case_style: Optional[str] = None
    evidence_style: Optional[str] = None
    execution_channel: Optional[str] = None
    data_origin: Optional[str] = None
    stage: str
    status: str
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    stage_events: list[StageEventRead] = []
    analyst_email: Optional[str] = None


class StageChangeRequest(BaseModel):
    direction: Literal["forward", "back"]


class StageAddRequest(BaseModel):
    stage: str


class StageDataOriginUpdate(BaseModel):
    """When data_origin changes, service_rest_json may auto-activate stages."""
    data_origin: str

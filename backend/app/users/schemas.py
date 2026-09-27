import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "analyst"


class UserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class LlmConfigIn(BaseModel):
    provider: str        # anthropic | ollama | fake
    api_key: str         # en texto plano; se cifra antes de guardar
    model: str | None = None
    base_url: str | None = None


class LlmConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    model: str | None
    base_url: str | None
    key_hint: str        # últimos 4 chars del key para mostrar en UI, ej. "...k29X"

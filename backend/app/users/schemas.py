import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


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
    email: str
    full_name: str
    password: str
    role: str = "analyst"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Dirección de correo inválida")
        return v


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

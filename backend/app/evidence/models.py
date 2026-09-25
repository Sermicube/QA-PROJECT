"""Modelos SQLAlchemy del módulo evidence."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    ocr_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    ocr_time_found: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ocr_url_found: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ocr_time_value: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ocr_url_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    accepted_with_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Execution(Base):
    __tablename__ = "executions"
    __table_args__ = (UniqueConstraint("test_case_id", name="uq_executions_test_case"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    result: Mapped[str] = mapped_column(String(20), nullable=False)  # passed | failed | blocked
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# Orden canónico de etapas (RF-02)
STAGE_ORDER: list[str] = [
    "context",
    "ambiguities",
    "testcases",
    "testdata",
    "execution",
    "deliverables",
    "closed",
]


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)          # bug | brecha
    external_code: Mapped[str] = mapped_column(String(100), nullable=False)
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    stage: Mapped[str] = mapped_column(String(30), nullable=False, default="context")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active | closed
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    stage_events: Mapped[list["StageEvent"]] = relationship(
        back_populates="certification", cascade="all, delete-orphan", lazy="selectin"
    )


class StageEvent(Base):
    __tablename__ = "stage_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    certification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("certifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    certification: Mapped[Certification] = relationship(back_populates="stage_events")

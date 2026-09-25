import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class TestCase(Base):
    """Caso de prueba con la plantilla estricta (RF-15, §6.4)."""

    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certifications.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)   # CP-01
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    preconditions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    expected_result: Mapped[str] = mapped_column(Text, nullable=False)
    # before | equal | after | None
    boundary: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # draft | approved
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    lint_results: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    criteria_links: Mapped[list["TestCaseCriterion"]] = relationship(
        back_populates="test_case", cascade="all, delete-orphan", lazy="selectin"
    )


class TestCaseCriterion(Base):
    """Relación N:M entre caso de prueba y criterio de aceptación."""

    __tablename__ = "test_case_criteria"

    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"),
        primary_key=True,
    )
    criterion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("acceptance_criteria.id", ondelete="CASCADE"),
        primary_key=True,
    )

    test_case: Mapped["TestCase"] = relationship(back_populates="criteria_links")

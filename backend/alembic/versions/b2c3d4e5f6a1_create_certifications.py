"""create certifications and stage_events tables

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-09-25

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a1"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "certifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("external_code", sa.String(100), nullable=False),
        sa.Column("module", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("stage", sa.String(30), nullable=False, server_default="requirement"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_certifications_owner_id"), "certifications", ["owner_id"], unique=False
    )

    op.create_table(
        "stage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "certification_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("certifications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_stage_events_certification_id"),
        "stage_events",
        ["certification_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_stage_events_certification_id"), table_name="stage_events")
    op.drop_table("stage_events")
    op.drop_index(op.f("ix_certifications_owner_id"), table_name="certifications")
    op.drop_table("certifications")

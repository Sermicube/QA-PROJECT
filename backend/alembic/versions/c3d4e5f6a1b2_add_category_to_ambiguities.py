"""add category to ambiguities

Revision ID: c3d4e5f6a1b2
Revises: f1a2b3c4d5e6
Create Date: 2026-10-20 10:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a1b2"
down_revision: str = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ambiguities",
        sa.Column(
            "category",
            sa.String(20),
            nullable=False,
            server_default="other",
        ),
    )


def downgrade() -> None:
    op.drop_column("ambiguities", "category")

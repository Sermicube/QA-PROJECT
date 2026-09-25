"""rename_stage_requirement_to_context

Revision ID: 16aa910b5eff
Revises: b2c3d4e5f6a1
Create Date: 2026-09-25 14:47:38.593932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '16aa910b5eff'
down_revision: Union[str, None] = 'b2c3d4e5f6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE certifications SET stage = 'context' WHERE stage = 'requirement'")
    op.execute("UPDATE stage_events SET stage = 'context' WHERE stage = 'requirement'")


def downgrade() -> None:
    op.execute("UPDATE certifications SET stage = 'requirement' WHERE stage = 'context'")
    op.execute("UPDATE stage_events SET stage = 'requirement' WHERE stage = 'context'")

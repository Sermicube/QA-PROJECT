"""phase0_recipes

Adds recipes, case_styles, case_patterns, inconclusive_reasons tables.
Adds recipe-related columns to certifications and status/source to stage_events.
Includes data migration for v1.1 certifications:
  - Stage rename: ambiguities/requirement → context, testdata → assignment,
    deliverables → documentation.
  - Backfill recipe_code and active_stages for existing rows.
  - Invariant: cert.stage is always active (required or optional) in active_stages.
    If the recipe marks the current stage as not_applicable (e.g. bug_simple marks
    assignment as not_applicable but a v1.1 cert was in testdata→assignment),
    the stage is promoted to optional so the cert is never stuck.

Revision ID: d0e1f2a3b4c5
Revises: 77891a244fba
Create Date: 2026-10-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, None] = '5a23325549d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# JSON strings for backfill (compact, no trailing commas)
_STAGES_BUG = (
    '{"context":"required","testcases":"required","format":"required",'
    '"data_request":"not_applicable","assignment":"not_applicable",'
    '"execution":"required","analysis":"not_applicable",'
    '"documentation":"required","review":"required","closed":"required"}'
)
_STAGES_BRECHA = (
    '{"context":"required","testcases":"required","format":"required",'
    '"data_request":"optional","assignment":"optional",'
    '"execution":"required","analysis":"not_applicable",'
    '"documentation":"required","review":"required","closed":"required"}'
)


def upgrade() -> None:
    # ── DDL: new tables ───────────────────────────────────────────────────────

    op.create_table(
        'recipes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=False, server_default=''),
        sa.Column('stages', postgresql.JSONB(), nullable=False),
        sa.Column('default_case_style', sa.String(50), nullable=False),
        sa.Column('default_evidence_style', sa.String(50), nullable=False, server_default='default'),
        sa.Column('default_execution_channel', sa.String(30), nullable=False),
        sa.Column('default_data_origin', sa.String(30), nullable=False),
        sa.Column('suggested_case_pattern', sa.String(50), nullable=False),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_recipes_code', 'recipes', ['code'])

    op.create_table(
        'case_styles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('fields', postgresql.JSONB(), nullable=False),
        sa.Column('template_jinja', sa.String(2000), nullable=False, server_default=''),
        sa.Column('lint_rules', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('example', sa.String(1000), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_case_styles_code', 'case_styles', ['code'])

    op.create_table(
        'case_patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=False, server_default=''),
        sa.Column('n_cases_typical', sa.String(20), nullable=True),
        sa.Column('notes', sa.String(500), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_case_patterns_code', 'case_patterns', ['code'])

    op.create_table(
        'inconclusive_reasons',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('label', sa.String(200), nullable=False),
        sa.Column('description', sa.String(500), nullable=False, server_default=''),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_inconclusive_reasons_code', 'inconclusive_reasons', ['code'])

    # ── DDL: new columns ──────────────────────────────────────────────────────

    op.add_column('certifications', sa.Column('service', sa.String(100), nullable=True))
    op.add_column('certifications', sa.Column('recipe_code', sa.String(50), nullable=True))
    op.add_column('certifications', sa.Column('active_stages', postgresql.JSONB(), nullable=True))
    op.add_column('certifications', sa.Column('case_style', sa.String(50), nullable=True))
    op.add_column('certifications', sa.Column('evidence_style', sa.String(50), nullable=True))
    op.add_column('certifications', sa.Column('execution_channel', sa.String(30), nullable=True))
    op.add_column('certifications', sa.Column('data_origin', sa.String(30), nullable=True))
    op.create_index('ix_certifications_recipe_code', 'certifications', ['recipe_code'])

    op.add_column('stage_events', sa.Column('status', sa.String(20), nullable=True))
    op.add_column('stage_events', sa.Column('source', sa.String(20), nullable=True))

    # ── DML: map old v1.1 stage names ────────────────────────────────────────
    # Old STAGE_ORDER: context, ambiguities, testcases, testdata, execution, deliverables, closed
    # Old schema also had 'requirement' as alias for 'context' in some paths.
    # New STAGE_ORDER: context, testcases, format, data_request, assignment,
    #                  execution, analysis, documentation, review, closed

    op.execute(sa.text("""
        UPDATE certifications
        SET stage = CASE stage
            WHEN 'ambiguities'  THEN 'context'
            WHEN 'requirement'  THEN 'context'
            WHEN 'testdata'     THEN 'assignment'
            WHEN 'deliverables' THEN 'documentation'
            ELSE stage
        END
        WHERE stage IN ('ambiguities', 'requirement', 'testdata', 'deliverables')
    """))

    op.execute(sa.text("""
        UPDATE stage_events
        SET stage = CASE stage
            WHEN 'ambiguities'  THEN 'context'
            WHEN 'requirement'  THEN 'context'
            WHEN 'testdata'     THEN 'assignment'
            WHEN 'deliverables' THEN 'documentation'
            ELSE stage
        END
        WHERE stage IN ('ambiguities', 'requirement', 'testdata', 'deliverables')
    """))

    # ── DML: backfill stage_events.status and source ──────────────────────────

    op.execute(sa.text("""
        UPDATE stage_events
        SET status = 'executed', source = 'recipe'
        WHERE status IS NULL
    """))

    # ── DML: backfill recipe_code ─────────────────────────────────────────────
    # Heuristic: type=bug → bug_simple; type=brecha → brecha_date_rule.
    # Analysts can correct later via PATCH /certifications/{id}.

    op.execute(sa.text("""
        UPDATE certifications
        SET recipe_code = CASE
            WHEN type = 'bug'    THEN 'bug_simple'
            WHEN type = 'brecha' THEN 'brecha_date_rule'
            ELSE 'bug_simple'
        END
        WHERE recipe_code IS NULL
    """))

    # ── DML: backfill active_stages and other recipe defaults ─────────────────
    # No certification can be left with active_stages IS NULL (RF-01b).

    op.execute(sa.text(
        f"""
        UPDATE certifications
        SET
            active_stages = CASE recipe_code
                WHEN 'bug_simple'       THEN '{_STAGES_BUG}'::jsonb
                WHEN 'brecha_date_rule' THEN '{_STAGES_BRECHA}'::jsonb
                ELSE                         '{_STAGES_BUG}'::jsonb
            END,
            case_style = CASE recipe_code
                WHEN 'brecha_date_rule' THEN 'validate_that'
                ELSE 'short'
            END,
            execution_channel = 'ui',
            data_origin       = CASE recipe_code
                WHEN 'brecha_date_rule' THEN 'colleague_request'
                ELSE 'developer_case'
            END,
            evidence_style    = 'default'
        WHERE active_stages IS NULL
        """
    ))


    # ── DML: guarantee cert.stage is always active in active_stages ──────────────
    # A v1.1 cert in testdata (→ assignment) assigned to bug_simple would have
    # active_stages['assignment'] = 'not_applicable', leaving the cert stuck.
    # Promote to 'optional' any stage that is the cert's current stage but was
    # marked not_applicable by the recipe backfill.

    op.execute(sa.text("""
        UPDATE certifications
        SET active_stages = active_stages || jsonb_build_object(stage, 'optional')
        WHERE active_stages IS NOT NULL
          AND active_stages ? stage
          AND (active_stages ->> stage) = 'not_applicable'
    """))


def downgrade() -> None:
    # ── DML: best-effort reverse of stage renames ────────────────────────────
    # Cannot fully restore old values since the mapping is many-to-one.
    # 'context' could have been 'context', 'ambiguities', or 'requirement'.
    # 'assignment' → restore to 'testdata'; 'documentation' → 'deliverables'.

    op.execute(sa.text("""
        UPDATE certifications
        SET stage = CASE stage
            WHEN 'assignment'   THEN 'testdata'
            WHEN 'documentation' THEN 'deliverables'
            ELSE stage
        END
        WHERE stage IN ('assignment', 'documentation')
    """))

    op.execute(sa.text("""
        UPDATE stage_events
        SET stage = CASE stage
            WHEN 'assignment'    THEN 'testdata'
            WHEN 'documentation' THEN 'deliverables'
            ELSE stage
        END
        WHERE stage IN ('assignment', 'documentation')
    """))

    # ── DDL: drop new columns and tables ─────────────────────────────────────

    op.drop_column('stage_events', 'source')
    op.drop_column('stage_events', 'status')

    op.drop_index('ix_certifications_recipe_code', 'certifications')
    op.drop_column('certifications', 'data_origin')
    op.drop_column('certifications', 'execution_channel')
    op.drop_column('certifications', 'evidence_style')
    op.drop_column('certifications', 'case_style')
    op.drop_column('certifications', 'active_stages')
    op.drop_column('certifications', 'recipe_code')
    op.drop_column('certifications', 'service')

    op.drop_index('ix_inconclusive_reasons_code', 'inconclusive_reasons')
    op.drop_table('inconclusive_reasons')
    op.drop_index('ix_case_patterns_code', 'case_patterns')
    op.drop_table('case_patterns')
    op.drop_index('ix_case_styles_code', 'case_styles')
    op.drop_table('case_styles')
    op.drop_index('ix_recipes_code', 'recipes')
    op.drop_table('recipes')

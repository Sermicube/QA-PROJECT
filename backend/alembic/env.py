import os
from logging.config import fileConfig

from sqlalchemy import Connection, create_engine, pool

from alembic import context

from app.core.config import settings
from app.core.db import Base
import app.users.models  # noqa: F401 — registers User with Base.metadata
import app.certifications.models  # noqa: F401 — registers Certification + StageEvent
import app.context.models  # noqa: F401 — registers ContextSource, AcceptanceCriterion, Ambiguity
import app.testcases.models  # noqa: F401 — registers TestCase, TestCaseCriterion
import app.testdata.models  # noqa: F401 — registers DomainField, ColumnMapping, UserBase, etc.
import app.evidence.models  # noqa: F401 — registers Evidence, Execution
import app.deliverables.models  # noqa: F401 — registers Deliverable, Template
import app.metrics.models  # noqa: F401 — registers ReworkEvent, BaselineCertification, LlmCall
import app.recipes.models  # noqa: F401 — registers Recipe, CaseStyle, CasePattern, InconclusiveReason

config = context.config

# ALEMBIC_DATABASE_URL lets you override the URL when running from the host
# (where Docker hostnames like 'postgres' are not resolvable).
# Falls back to settings.DATABASE_URL with asyncpg→psycopg2 substitution.
_migration_url = os.environ.get("ALEMBIC_DATABASE_URL") or settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)
config.set_main_option("sqlalchemy.url", _migration_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_migration_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

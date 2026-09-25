import os

# Deben estar antes de cualquier import de app para que pydantic-settings los lea
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-32b+")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://copiloto:copiloto@localhost:5432/copiloto"
)

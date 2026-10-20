"""RF-12 — Verifica que el módulo context.tasks registra todos los modelos
necesarios con el mapper de SQLAlchemy antes de abrir una sesión.

Sin los imports de certifications.models el mapper no puede resolver la FK
ambiguities.certification_id → certifications.id y lanza NoReferencedTableError
durante el primer flush.
"""
import importlib
import sys


def _clear_app_modules() -> None:
    """Remove cached app modules so imports are re-executed from scratch."""
    to_remove = [k for k in sys.modules if k.startswith("app.")]
    for k in to_remove:
        del sys.modules[k]


def test_context_tasks_registers_certifications_model() -> None:
    """After importing context.tasks, certifications model must be in the mapper."""
    _clear_app_modules()

    import app.context.tasks  # noqa: F401 — triggers the imports inside _analyze

    # Import the mapper registry — available after any SQLAlchemy model import
    from sqlalchemy.orm import class_mapper
    from app.certifications.models import Certification
    from app.context.models import Ambiguity

    # Both models must be mappable (i.e. registered with the Base metadata)
    mapper_cert = class_mapper(Certification)
    mapper_amb = class_mapper(Ambiguity)

    assert mapper_cert is not None
    assert mapper_amb is not None

    # The FK target table must be resolvable: iterate FK columns on Ambiguity
    from sqlalchemy import inspect as sa_inspect
    insp = sa_inspect(Ambiguity)
    fk_tables = {
        fk.column.table.name
        for col in insp.mapper.columns.values()
        for fk in col.foreign_keys
    }
    assert "certifications" in fk_tables, (
        "Ambiguity FK to 'certifications' not resolvable — missing model import in tasks.py"
    )


def test_context_task_module_imports_all_required_models() -> None:
    """Explicitly verify the three noqa imports are present in tasks.py source."""
    import inspect
    import app.context.tasks as tasks_mod

    source = inspect.getsource(tasks_mod)
    for required in [
        "app.certifications.models",
        "app.context.models",
        "app.users.models",
    ]:
        assert required in source, (
            f"tasks.py is missing 'import {required}' — "
            "this will cause NoReferencedTableError at runtime"
        )

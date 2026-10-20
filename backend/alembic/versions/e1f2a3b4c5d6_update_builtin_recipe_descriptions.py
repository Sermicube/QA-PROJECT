"""update builtin recipe descriptions to user-friendly language

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-10-19

"""
from alembic import op
from sqlalchemy import text

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d0e1f2a3b4c5"
branch_labels: str | None = None
depends_on: str | None = None

_DESCRIPTIONS: dict[str, str] = {
    "bug_simple": "Bug con un único escenario de prueba.",
    "bug_before_after": "Bug que se demuestra comparando el comportamiento antes y después de la corrección.",
    "bug_negative_control": "Reproduce el bug y verifica que el comportamiento válido del sistema sigue funcionando.",
    "brecha_date_rule": "Brecha funcional cuya validación gira en torno a una comparación de fechas.",
    "service_soap_xml": (
        "Certificación de un servicio SOAP/XML. "
        "Activa las diez etapas: contexto, casos, formato, solicitud a fábrica, "
        "asignación de usuarios, ejecución, análisis, documentación, revisión y cierre."
    ),
    "service_rest_json": (
        "Certificación de un servicio REST con análisis por JSONPath. "
        "Solicitud a fábrica y asignación de usuarios son opcionales; "
        "se activan cuando el origen de datos es 'Solicitud a fábrica'."
    ),
    "file_batch": "Proceso de cargue masivo de archivo o ejecución de proceso por lotes.",
    "client_cases": "El cliente entrega su propio plan de pruebas. El analista lo importa y ejecuta.",
}


def upgrade() -> None:
    conn = op.get_bind()
    for code, desc in _DESCRIPTIONS.items():
        conn.execute(
            text("UPDATE recipes SET description = :desc WHERE code = :code AND is_builtin = true"),
            {"desc": desc, "code": code},
        )


def downgrade() -> None:
    pass

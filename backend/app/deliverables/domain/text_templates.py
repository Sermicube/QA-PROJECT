"""Generación de nota TFS y correo con Jinja2 (RF-41, RF-42)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape([]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_tfs_note(cert: dict, cases: list[dict]) -> str:
    """Renderiza templates/tfs_note.md.j2."""
    env = _env()
    tmpl = env.get_template("tfs_note.md.j2")
    all_passed = all(c.get("result") == "passed" for c in cases if c.get("result"))
    return tmpl.render(
        cert=cert,
        cases=cases,
        today=date.today().strftime("%d/%m/%Y"),
        all_passed=all_passed,
    )


def render_email(cert: dict, cases: list[dict], analyst_name: str = "El analista") -> str:
    """Renderiza templates/email.md.j2."""
    env = _env()
    tmpl = env.get_template("email.md.j2")
    all_passed = all(c.get("result") == "passed" for c in cases if c.get("result"))
    return tmpl.render(
        cert=cert,
        cases=cases,
        today=date.today().strftime("%d/%m/%Y"),
        all_passed=all_passed,
        analyst_name=analyst_name,
    )

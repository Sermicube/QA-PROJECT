"""Extracción de texto y secciones de documentos .docx y .pdf (RF-11)."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Section:
    title: str
    content: str
    level: int  # 1 = heading 1, 2 = heading 2, …


def extract_docx(path: str | Path) -> tuple[str, list[Section]]:
    """Extrae texto plano y secciones de un archivo .docx."""
    from docx import Document  # type: ignore[import-untyped]

    doc = Document(str(path))
    sections: list[Section] = []
    current_title = "Introducción"
    current_level = 1
    current_lines: list[str] = []
    full_lines: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        full_lines.append(text)

        style_name = para.style.name if para.style else ""
        heading_match = re.match(r"Heading\s+(\d+)", style_name, re.IGNORECASE)

        if heading_match:
            # Guardar sección anterior
            if current_lines:
                sections.append(Section(
                    title=current_title,
                    content="\n".join(current_lines),
                    level=current_level,
                ))
                current_lines = []
            current_title = text
            current_level = int(heading_match.group(1))
        else:
            current_lines.append(text)

    # Última sección
    if current_lines:
        sections.append(Section(
            title=current_title,
            content="\n".join(current_lines),
            level=current_level,
        ))

    return "\n".join(full_lines), sections


def extract_pdf(path: str | Path) -> tuple[str, list[Section]]:
    """Extrae texto plano y secciones heurísticas de un PDF."""
    import pdfplumber  # type: ignore[import-untyped]

    all_lines: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_lines.extend(text.splitlines())

    full_text = "\n".join(line for line in all_lines if line.strip())
    sections = _heuristic_sections(full_text)
    return full_text, sections


def extract_from_bytes(data: bytes, mime_type: str, file_name: str) -> tuple[str, list[Section]]:
    """Extrae texto desde bytes en memoria, eligiendo el extractor según el tipo."""
    import tempfile

    suffix = Path(file_name).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        if suffix == ".docx":
            return extract_docx(tmp_path)
        if suffix == ".pdf":
            return extract_pdf(tmp_path)
        # Fallback: tratar como texto plano
        text = data.decode("utf-8", errors="replace")
        return text, _heuristic_sections(text)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _heuristic_sections(text: str) -> list[Section]:
    """Divide el texto en secciones usando numeración o líneas en mayúsculas."""
    sections: list[Section] = []
    # Detecta títulos numerados: "1.", "1.1", "2.3.1" o líneas en MAYÚSCULAS cortas
    heading_re = re.compile(
        r"^(?:(\d+(?:\.\d+)*)\s+(.+)|([A-ZÁÉÍÓÚ][A-ZÁÉÍÓÚ\s]{3,60}))$"
    )
    current_title = "Contenido"
    current_level = 1
    current_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        m = heading_re.match(stripped)
        if m:
            if current_lines:
                sections.append(Section(current_title, "\n".join(current_lines), current_level))
                current_lines = []
            if m.group(1):
                level = m.group(1).count(".") + 1
                current_title = f"{m.group(1)} {m.group(2)}"
                current_level = level
            else:
                current_title = m.group(3)
                current_level = 1
        else:
            current_lines.append(stripped)

    if current_lines:
        sections.append(Section(current_title, "\n".join(current_lines), current_level))

    return sections or [Section("Contenido", text, 1)]

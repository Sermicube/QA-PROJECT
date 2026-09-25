"""Generación del ZIP de entregables (RF-43)."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path


def build_zip(cert_id: str, files: list[dict]) -> bytes:
    """Empaqueta archivos en ZIP en memoria.

    files: [{"path": str, "arcname": str}]
    Solo incluye archivos que existan en disco.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for entry in files:
            src = Path(entry["path"])
            if src.exists():
                zf.write(src, arcname=entry.get("arcname", src.name))
    buf.seek(0)
    return buf.read()

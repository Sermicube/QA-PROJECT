"""Tarea Celery para validación OCR de pantallazos (RF-32)."""
from __future__ import annotations

import asyncio
import uuid

from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="evidence.validate_ocr")
def validate_ocr(self: object, evidence_id_str: str) -> dict:
    return asyncio.run(_validate_ocr(evidence_id_str))


async def _validate_ocr(evidence_id_str: str) -> dict:
    from app.core.db import async_session_factory
    from app.evidence.domain.ocr import validate_screenshot
    from app.evidence.repository import EvidenceRepository
    from pathlib import Path

    evidence_id = uuid.UUID(evidence_id_str)

    async with async_session_factory() as session:
        repo = EvidenceRepository(session)
        ev = await repo.get_evidence(evidence_id)
        if ev is None:
            return {"error": f"Evidence {evidence_id} no encontrada"}

        try:
            data = Path(ev.file_path).read_bytes()
        except OSError as e:
            return {"error": f"No se pudo leer el archivo: {e}"}

        result = validate_screenshot(data)
        await repo.update_ocr(evidence_id, result)
        await session.commit()

        return {
            "status": result.status,
            "time_found": result.time_found,
            "url_found": result.url_found,
        }

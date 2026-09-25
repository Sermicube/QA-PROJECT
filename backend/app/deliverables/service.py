"""Lógica de negocio del módulo deliverables (RF-40 a RF-44)."""
from __future__ import annotations

import uuid

from app.deliverables.models import Deliverable
from app.deliverables.repository import DeliverableRepository


class DeliverableError(Exception):
    pass


class DeliverableService:
    def __init__(self, repo: DeliverableRepository) -> None:
        self._repo = repo

    async def generate_all(self, cert_id: uuid.UUID, user_id_str: str | None = None) -> str:
        """Encola la tarea de generación. Devuelve task_id."""
        from app.deliverables.tasks import generate_deliverables as celery_task
        task = celery_task.delay(str(cert_id), user_id_str)
        return task.id

    async def get_deliverables(self, cert_id: uuid.UUID) -> list[Deliverable]:
        return await self._repo.list_by_cert(cert_id)

    async def update_content(self, deliverable_id: uuid.UUID, content: str) -> Deliverable:
        d = await self._repo.get(deliverable_id)
        if d is None:
            raise DeliverableError(f"Entregable {deliverable_id} no encontrado")
        return await self._repo.upsert(d.certification_id, d.kind, content=content)

    async def get_download_path(self, deliverable_id: uuid.UUID) -> str:
        d = await self._repo.get(deliverable_id)
        if d is None:
            raise DeliverableError(f"Entregable {deliverable_id} no encontrado")
        if not d.file_path:
            raise DeliverableError("Este entregable no tiene archivo descargable")
        return d.file_path

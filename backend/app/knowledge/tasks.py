"""Tareas Celery del módulo knowledge (RF-60)."""
from __future__ import annotations

import asyncio
import uuid

from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="knowledge.ingest_certification")
def ingest_certification(self: object, cert_id_str: str, user_id_str: str | None = None) -> dict:
    return asyncio.run(_ingest(cert_id_str, user_id_str))


async def _ingest(cert_id_str: str, user_id_str: str | None = None) -> dict:
    from app.core.db import async_session_factory
    from app.core.neo4j_client import get_driver
    from app.knowledge.repository import KnowledgeRepository
    from app.knowledge.service import KnowledgeService

    cert_id = uuid.UUID(cert_id_str)
    driver = get_driver()
    repo = KnowledgeRepository(driver)
    svc = KnowledgeService(repo)

    async with async_session_factory() as session:
        return await svc.ingest_certification(cert_id, session)

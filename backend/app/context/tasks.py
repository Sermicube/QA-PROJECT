"""Tareas Celery del módulo context (RF-12, RF-13 — análisis LLM)."""
from __future__ import annotations

import asyncio
import uuid

from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="context.analyze")
def analyze_context(self: object, certification_id_str: str, user_id_str: str | None = None) -> dict:
    """Extrae criterios y detecta ambigüedades semánticas vía LLM."""
    return asyncio.run(_analyze(certification_id_str, user_id_str))


async def _analyze(certification_id_str: str, user_id_str: str | None = None) -> dict:
    import json

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.context.repository import ContextRepository
    from app.context.service import ContextService
    from app.core.db import async_session_factory
    from app.core.config import settings
    from app.llm.factory import get_provider, get_provider_for_user
    from app.llm.pii_guard import PIIGuard
    from app.llm.provider import Message

    cert_id = uuid.UUID(certification_id_str)
    pii_guard = PIIGuard()
    llm = (await get_provider_for_user(user_id_str) if user_id_str else get_provider())

    async with async_session_factory() as session:
        repo = ContextRepository(session)
        svc = ContextService(repo)

        # 1. Obtener fuentes
        sources = await svc.get_sources(cert_id)
        if not sources:
            return {"criteria": 0, "ambiguities": 0, "error": "no_sources"}

        # 2. Construir contexto enmascarado
        context_text = svc._build_context_text(sources)

        # 3. Extraer criterios vía LLM
        criteria_items = await _extract_criteria(llm, pii_guard, context_text, sources)

        # 4. Persistir criterios
        await repo.replace_criteria(cert_id, criteria_items)

        # 5. Detección local de ambigüedades (rápida, determinística)
        await svc.run_local_ambiguity_scan(cert_id)

        # 6. Detección semántica de ambigüedades vía LLM
        semantic_items = await _detect_semantic_ambiguities(llm, pii_guard, context_text, sources)
        if semantic_items:
            await repo.add_ambiguities(cert_id, semantic_items)

        return {"criteria": len(criteria_items), "ambiguities": len(semantic_items)}


async def _extract_criteria(llm: object, pii_guard: object, context_text: str, sources: list) -> list[dict]:
    from pathlib import Path
    from pydantic import BaseModel
    from app.llm.provider import Message, LLMProvider

    assert isinstance(llm, LLMProvider)  # type: ignore[misc]

    prompt_path = Path(__file__).parent.parent / "llm" / "prompts" / "extract_criteria.v1.md"
    system = prompt_path.read_text(encoding="utf-8")

    # Construir lista de fuentes para el prompt
    source_list = "\n\n".join(
        f"### {s.kind}\n{s.extracted_text or ''}" for s in sources
    )
    masked_list, _ = pii_guard.mask(source_list)  # type: ignore[attr-defined]

    messages = [Message(role="user", content=f"Contexto de la certificación:\n\n{masked_list}")]

    class CriteriaResponse(BaseModel):
        items: list[dict]

    try:
        raw = await llm.complete(system=system, messages=messages, max_tokens=2048)
        import json, re
        # Extraer JSON del texto
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass
    return []


async def _detect_semantic_ambiguities(llm: object, pii_guard: object, context_text: str, sources: list) -> list[dict]:
    from pathlib import Path
    from app.llm.provider import Message, LLMProvider

    assert isinstance(llm, LLMProvider)  # type: ignore[misc]

    prompt_path = Path(__file__).parent.parent / "llm" / "prompts" / "detect_ambiguities.v1.md"
    system = prompt_path.read_text(encoding="utf-8")
    masked, _ = pii_guard.mask(context_text)  # type: ignore[attr-defined]

    messages = [Message(role="user", content=f"Contexto:\n\n{masked}")]
    try:
        raw = await llm.complete(system=system, messages=messages, max_tokens=1024)
        import json, re
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass
    return []

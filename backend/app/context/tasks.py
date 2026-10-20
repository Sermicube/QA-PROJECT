"""Tareas Celery del módulo context (RF-12, RF-13 — análisis LLM)."""
from __future__ import annotations

import asyncio
import uuid

from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="context.analyze")
def analyze_context(self: object, certification_id_str: str, user_id_str: str | None = None) -> dict:
    """Extrae criterios y detecta ambigüedades semánticas vía LLM."""
    # Each asyncio.run() creates a new event loop. Dispose the async engine's
    # connection pool first so asyncpg doesn't try to reuse connections tied to
    # a previous loop ("Future attached to a different loop" error).
    from app.core.db import engine
    engine.sync_engine.dispose()
    return asyncio.run(_analyze(certification_id_str, user_id_str))


async def _analyze(certification_id_str: str, user_id_str: str | None = None) -> dict:
    # Register all models with the SQLAlchemy mapper BEFORE opening any session.
    # Without these imports the mapper cannot resolve FK targets (e.g.
    # ambiguities.certification_id → certifications.id) and raises
    # NoReferencedTableError on the first flush.
    import app.certifications.models  # noqa: F401
    import app.context.models  # noqa: F401
    import app.users.models  # noqa: F401

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

    try:
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

            # 5. Extraer resumen de negocio vía LLM y persistir como fuente especial
            summary_data = await _extract_summary(llm, pii_guard, context_text)
            if summary_data:
                await repo.upsert_source(cert_id, "analysis_summary", content=summary_data)

            # 6. Detección local de ambigüedades (rápida, determinística)
            await svc.run_local_ambiguity_scan(cert_id)

            # 7. Detección semántica de ambigüedades vía LLM
            semantic_items = await _detect_semantic_ambiguities(llm, pii_guard, context_text, sources)
            if semantic_items:
                await repo.add_ambiguities(cert_id, semantic_items)

            return {"criteria": len(criteria_items), "ambiguities": len(semantic_items)}
    except Exception as exc:
        import structlog
        structlog.get_logger().error("context_analyze_failed", error=str(exc), exc_info=True)
        raise


def _parse_json_array(raw: str) -> list:
    """Extract a JSON array from a LLM response that may be wrapped in markdown fences."""
    import json, re
    # Try fenced code block first: ```json\n[...]\n```
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            pass
    # Fallback: bare array anywhere in the text
    arr = re.search(r"\[.*\]", raw, re.DOTALL)
    if arr:
        try:
            return json.loads(arr.group())
        except Exception:
            pass
    return []


async def _extract_criteria(llm: object, pii_guard: object, context_text: str, sources: list) -> list[dict]:
    from pathlib import Path
    from app.llm.provider import Message, LLMProvider

    assert isinstance(llm, LLMProvider)  # type: ignore[misc]

    prompt_path = Path(__file__).parent.parent / "llm" / "prompts" / "extract_criteria.v1.md"
    system = prompt_path.read_text(encoding="utf-8")

    # context_text is already PII-masked by _build_context_text (includes analyst_description content)
    messages = [Message(role="user", content=f"Contexto de la certificación:\n\n{context_text}")]

    try:
        raw = await llm.complete(system=system, messages=messages, max_tokens=4096)
        return _parse_json_array(raw)
    except Exception:
        pass
    return []


async def _extract_summary(llm: object, pii_guard: object, context_text: str) -> dict:
    """Returns {business_summary: str, rules: list[str]} or {} on failure."""
    import json, re
    from pathlib import Path
    from app.llm.provider import Message, LLMProvider

    assert isinstance(llm, LLMProvider)  # type: ignore[misc]

    prompt_path = Path(__file__).parent.parent / "llm" / "prompts" / "extract_summary.v1.md"
    system = prompt_path.read_text(encoding="utf-8")
    masked, _ = pii_guard.mask(context_text)  # type: ignore[attr-defined]

    messages = [Message(role="user", content=f"Contexto:\n\n{masked}")]
    try:
        raw = await llm.complete(system=system, messages=messages, max_tokens=2048)
        # Try fenced JSON object
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if fence:
            data = json.loads(fence.group(1))
            if "business_summary" in data:
                return data
        # Try bare JSON object
        obj_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if obj_match:
            data = json.loads(obj_match.group())
            if "business_summary" in data:
                return data
        # Fallback: treat full response as summary text
        return {"business_summary": raw.strip(), "rules": []}
    except Exception:
        return {}


async def _detect_semantic_ambiguities(llm: object, pii_guard: object, context_text: str, sources: list) -> list[dict]:
    from pathlib import Path
    from app.llm.provider import Message, LLMProvider

    assert isinstance(llm, LLMProvider)  # type: ignore[misc]

    prompt_path = Path(__file__).parent.parent / "llm" / "prompts" / "detect_ambiguities.v1.md"
    system = prompt_path.read_text(encoding="utf-8")
    masked, _ = pii_guard.mask(context_text)  # type: ignore[attr-defined]

    messages = [Message(role="user", content=f"Contexto:\n\n{masked}")]
    try:
        raw = await llm.complete(system=system, messages=messages, max_tokens=4096)
        return _parse_json_array(raw)
    except Exception:
        pass
    return []

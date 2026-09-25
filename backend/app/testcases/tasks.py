"""Tarea Celery para generación de casos de prueba vía LLM (RF-15)."""
from __future__ import annotations

import asyncio
import uuid

from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="testcases.generate")
def generate_cases(self: object, certification_id_str: str) -> dict:
    return asyncio.run(_generate(certification_id_str))


async def _generate(certification_id_str: str) -> dict:
    import json
    import re
    from pathlib import Path

    from app.context.repository import ContextRepository
    from app.context.service import ContextService
    from app.core.db import async_session_factory
    from app.llm.factory import get_provider
    from app.llm.pii_guard import PIIGuard
    from app.llm.provider import Message, LLMProvider
    from app.testcases.repository import TestCaseRepository
    from app.testcases.service import TestCaseService

    cert_id = uuid.UUID(certification_id_str)
    pii_guard = PIIGuard()
    llm = get_provider()
    assert isinstance(llm, LLMProvider)  # type: ignore[misc]

    prompt_path = Path(__file__).parent.parent / "llm" / "prompts" / "generate_cases.v1.md"
    system = prompt_path.read_text(encoding="utf-8")

    async with async_session_factory() as session:
        ctx_repo = ContextRepository(session)
        tc_repo = TestCaseRepository(session)
        svc = ContextService(ctx_repo)
        tc_svc = TestCaseService(tc_repo, ctx_repo)

        # Contexto
        sources = await svc.get_sources(cert_id)
        context_text = svc._build_context_text(sources)

        # Criterios y resoluciones de ambigüedades
        criteria = await svc.get_criteria(cert_id)
        ambiguities = await svc.get_ambiguities(cert_id)
        resolutions = "\n".join(
            f"- {a.question} → {a.resolution}"
            for a in ambiguities
            if a.resolution
        )

        criteria_list = "\n".join(f"{c.code}: {c.text}" for c in criteria)
        user_content = (
            f"Contexto:\n{context_text}\n\n"
            f"Criterios de aceptación:\n{criteria_list}\n\n"
            f"Resoluciones de ambigüedades:\n{resolutions or 'Ninguna registrada.'}"
        )
        masked, _ = pii_guard.mask(user_content)

        messages = [Message(role="user", content=masked)]
        try:
            raw = await llm.complete(system=system, messages=messages, max_tokens=4096)
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                cases_data = json.loads(match.group())
                created = await tc_svc.import_cases(cert_id, cases_data)
                return {"cases_created": len(created)}
        except Exception as exc:
            return {"error": str(exc)}

    return {"cases_created": 0}

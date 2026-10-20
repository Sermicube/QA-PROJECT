"""Tarea Celery para generación de casos de prueba vía LLM (RF-15)."""
from __future__ import annotations

import asyncio
import uuid

from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="testcases.generate")
def generate_cases(self: object, certification_id_str: str, user_id_str: str | None = None) -> dict:
    from app.core.db import engine
    engine.sync_engine.dispose()
    return asyncio.run(_generate(certification_id_str, user_id_str))


async def _generate(certification_id_str: str, user_id_str: str | None = None) -> dict:
    import json
    import re
    from pathlib import Path

    import app.certifications.models  # noqa: F401
    import app.context.models  # noqa: F401
    import app.testcases.models  # noqa: F401
    import app.users.models  # noqa: F401

    from app.certifications.repository import CertificationRepository
    from app.context.repository import ContextRepository
    from app.context.service import ContextService
    from app.core.db import async_session_factory
    from app.llm.factory import get_provider, get_provider_for_user
    from app.llm.pii_guard import PIIGuard
    from app.llm.provider import Message, LLMProvider
    from app.testcases.repository import TestCaseRepository
    from app.testcases.service import TestCaseService

    cert_id = uuid.UUID(certification_id_str)
    pii_guard = PIIGuard()
    llm = (await get_provider_for_user(user_id_str) if user_id_str else get_provider())
    assert isinstance(llm, LLMProvider)  # type: ignore[misc]

    prompt_path = Path(__file__).parent.parent / "llm" / "prompts" / "generate_cases.v1.md"
    system = prompt_path.read_text(encoding="utf-8")

    async with async_session_factory() as session:
        cert_repo = CertificationRepository(session)
        ctx_repo = ContextRepository(session)
        tc_repo = TestCaseRepository(session)
        svc = ContextService(ctx_repo)
        tc_svc = TestCaseService(tc_repo, ctx_repo)

        cert = await cert_repo.get_by_id(cert_id)
        case_style = (cert.case_style or "validate_that") if cert else "validate_that"

        sources = await svc.get_sources(cert_id)
        context_text = svc._build_context_text(sources)

        criteria = await svc.get_criteria(cert_id)
        ambiguities = await svc.get_ambiguities(cert_id)

        resolved = [a for a in ambiguities if a.resolution]
        unresolved = [a for a in ambiguities if not a.resolution]

        resolutions_text = "\n".join(
            f"- {a.question} → {a.resolution}" for a in resolved
        ) or "Ninguna registrada."

        unresolved_text = "\n".join(
            f"- {a.question}" for a in unresolved
        ) or "Ninguna."

        criteria_list = "\n".join(f"{c.code}: {c.text}" for c in criteria)

        # Rules from analysis summary — every rule needs at least one case (see generate_cases prompt)
        summary_source = next((s for s in sources if s.kind == "analysis_summary"), None)
        rules_list: list[str] = []
        if summary_source and summary_source.content:
            rules_list = (summary_source.content or {}).get("rules", []) or []
        rules_text = "\n".join(f"- {r}" for r in rules_list) or "Ninguna extraída."

        user_content = (
            f"caso_style: {case_style}\n\n"
            f"Contexto:\n{context_text}\n\n"
            f"Criterios de aceptación:\n{criteria_list}\n\n"
            f"Reglas de negocio extraídas:\n{rules_text}\n\n"
            f"Resoluciones de ambigüedades:\n{resolutions_text}\n\n"
            f"Ambigüedades no resueltas (marcar casos dependientes con pending_assumption):\n"
            f"{unresolved_text}"
        )
        masked, _ = pii_guard.mask(user_content)

        messages = [Message(role="user", content=masked)]
        try:
            raw = await llm.complete(system=system, messages=messages, max_tokens=4096)
            # Try fenced code block first (Anthropic wraps JSON in ```json ... ```)
            fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
            if fence:
                cases_data = json.loads(fence.group(1))
            else:
                match = re.search(r"\[.*\]", raw, re.DOTALL)
                cases_data = json.loads(match.group()) if match else []
            if cases_data:
                # Assign sequential order so they display in LLM-intended order
                for i, case in enumerate(cases_data):
                    case.setdefault("order", i)
                created = await tc_svc.import_cases(cert_id, cases_data)
                return {"cases_created": len(created)}
        except Exception as exc:
            return {"error": str(exc)}

    return {"cases_created": 0}

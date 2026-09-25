"""Tareas Celery del módulo testdata (RF-22, RF-23)."""
from __future__ import annotations

import asyncio
import uuid

from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="testdata.suggest_conditions")
def suggest_conditions(self: object, test_case_id_str: str) -> dict:
    return asyncio.run(_suggest_conditions(test_case_id_str))


@celery_app.task(bind=True, name="testdata.suggest_mapping_llm")
def suggest_mapping_llm(self: object, base_id_str: str) -> dict:
    return asyncio.run(_suggest_mapping_llm(base_id_str))


async def _suggest_conditions(test_case_id_str: str) -> dict:
    """LLM sugiere condiciones DSL a partir del nombre + criterios del caso.

    SEGURIDAD: nunca se envían datos de la base de usuarios al LLM.
    Solo llegan: nombre del caso, criterios de aceptación (texto) y los
    nombres de los campos de dominio disponibles en el mapeo confirmado.
    """
    import json
    import re
    from pathlib import Path

    from app.context.models import AcceptanceCriterion
    from app.context.repository import ContextRepository
    from app.core.db import async_session_factory
    from app.llm.factory import get_provider
    from app.llm.pii_guard import PIIGuard
    from app.llm.provider import Message
    from app.testcases.repository import TestCaseRepository
    from app.testdata.repository import TestDataRepository
    from sqlalchemy import select

    tc_id = uuid.UUID(test_case_id_str)
    pii_guard = PIIGuard()
    llm = get_provider()

    prompt_path = Path(__file__).parent.parent / "llm" / "prompts" / "suggest_conditions.v1.md"
    system = prompt_path.read_text(encoding="utf-8")

    async with async_session_factory() as session:
        tc_repo = TestCaseRepository(session)
        td_repo = TestDataRepository(session)

        tc = await tc_repo.get(tc_id)
        if tc is None:
            return {"error": f"Caso {tc_id} no encontrado"}

        # Criterios del caso
        criterion_ids = await tc_repo.get_criterion_links(tc_id)
        criteria = []
        for cid in criterion_ids:
            result = await session.execute(
                select(AcceptanceCriterion).where(AcceptanceCriterion.id == cid)
            )
            crit = result.scalar_one_or_none()
            if crit:
                criteria.append(f"{crit.code}: {crit.text}")

        # Campos disponibles en el mapeo confirmado de la certificación
        # Solo se envían keys y labels — NUNCA valores de filas
        available_fields = await td_repo.get_available_fields_for_cert(tc.certification_id)
        if available_fields:
            fields_block = "\n".join(
                f"- {f['key']} ({f['data_type']}): {f['label']}"
                for f in available_fields
            )
            fields_section = f"\n\nCampos disponibles en la base de usuarios de esta certificación:\n{fields_block}"
            fields_note = "IMPORTANTE: Usa SOLO los campos listados arriba en tus condiciones."
        else:
            fields_section = ""
            fields_note = (
                "No hay base de usuarios cargada aún. "
                "Usa los campos de dominio del sistema si los conoces del contexto del caso."
            )

        user_content = (
            f"Caso de prueba: {tc.name}\n\n"
            f"Criterios de aceptación:\n" + "\n".join(criteria or ["(sin criterios vinculados)"])
            + fields_section
            + f"\n\n{fields_note}"
        )

        masked_text, _ = pii_guard.mask(user_content)

        messages = [Message(role="user", content=masked_text)]
        try:
            raw = await llm.complete(system=system, messages=messages, max_tokens=2048)
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                result_dict = json.loads(match.group())
                await td_repo.upsert_conditions(
                    tc_id=tc_id,
                    conditions=result_dict.get("conditions", []),
                    derived_inputs=result_dict.get("derived_inputs", []),
                    mutates_state=result_dict.get("mutates_state", True),
                )
                await session.commit()
                return {"conditions_suggested": len(result_dict.get("conditions", []))}
        except Exception as exc:
            return {"error": str(exc)}

    return {"conditions_suggested": 0}


async def _suggest_mapping_llm(base_id_str: str) -> dict:
    """LLM sugiere mapeo a partir de nombres de columna y tipos detectados.

    SEGURIDAD: nunca se envían valores de filas al LLM. Solo nombres y tipos.
    """
    import json
    import re
    from pathlib import Path

    from app.core.db import async_session_factory
    from app.llm.factory import get_provider
    from app.llm.provider import Message
    from app.testdata.domain.loader import load_base, detect_column_types
    from app.testdata.repository import TestDataRepository

    base_id = uuid.UUID(base_id_str)
    llm = get_provider()

    prompt_path = Path(__file__).parent.parent / "llm" / "prompts" / "suggest_mapping.v1.md"
    system = prompt_path.read_text(encoding="utf-8")

    async with async_session_factory() as session:
        td_repo = TestDataRepository(session)
        base = await td_repo.get_base(base_id)
        if base is None:
            return {"error": f"Base {base_id} no encontrada"}

        from app.testdata.service import _mime_from_name
        mime = _mime_from_name(base.file_name)
        df = load_base(base.file_path, mime)
        col_types = detect_column_types(df)

        domain_fields = await td_repo.list_domain_fields()
        domain_list = "\n".join(f"- {f.key} ({f.data_type}): {f.label}" for f in domain_fields)

        col_info = "\n".join(f"- {col} ({col_types.get(col, 'text')})" for col in df.columns)
        user_content = (
            f"Columnas de la base:\n{col_info}\n\n"
            f"Campos de dominio disponibles:\n{domain_list}"
        )

        messages = [Message(role="user", content=user_content)]
        try:
            raw = await llm.complete(system=system, messages=messages, max_tokens=1024)
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                mapping = json.loads(match.group())
                return {"mapping": mapping}
        except Exception as exc:
            return {"error": str(exc)}

    return {"mapping": {}}

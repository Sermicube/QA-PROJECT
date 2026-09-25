"""Servicios del módulo Mapa Vivo (RF-60 a RF-63)."""
from __future__ import annotations

import re
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.repository import KnowledgeRepository

log = structlog.get_logger()


class KnowledgeService:
    def __init__(self, repo: KnowledgeRepository) -> None:
        self._repo = repo

    # ── RF-60: Ingestar al cerrar ─────────────────────────────────────────────

    async def ingest_certification(self, cert_id: uuid.UUID, session: AsyncSession) -> dict:
        """Lee datos de Postgres y registra en el grafo Neo4j."""
        from sqlalchemy import select

        from app.certifications.models import Certification
        from app.testcases.models import TestCase
        from app.testdata.models import Assignment

        cert = await session.get(Certification, cert_id)
        if cert is None:
            return {"error": "Certificación no encontrada"}

        result = await session.execute(
            select(TestCase).where(TestCase.certification_id == cert_id)
        )
        cases = result.scalars().all()

        cases_data = []
        for tc in cases:
            # Obtener resultado si existe
            assignment_result = await session.execute(
                select(Assignment).where(Assignment.test_case_id == tc.id)
            )
            assignment = assignment_result.scalar_one_or_none()
            tc_result = getattr(assignment, "result", "") or ""

            # Extraer features/rules de los pasos y resultado esperado
            features = _extract_features(tc.name, tc.steps or [])
            rules = _extract_rules(tc.expected_result or "")
            error_messages = _extract_messages(tc.expected_result or "")

            cases_data.append({
                "id": str(tc.id),
                "name": tc.name,
                "result": tc_result,
                "features": features,
                "rules": rules,
                "error_messages": error_messages,
            })

        cert_data = {
            "cert_id": str(cert.id),
            "title": cert.title,
            "type": cert.type,
            "module": cert.module,
            "cases": cases_data,
        }

        await self._repo.record_certification(cert_data)
        log.info("knowledge_ingest_done", cert_id=str(cert_id), cases=len(cases_data))
        return {"ingested_cases": len(cases_data)}

    # ── RF-61: Consulta en lenguaje natural ──────────────────────────────────

    async def natural_language_query(
        self,
        text: str,
        module_filter: str | None,
        llm,
    ) -> list[dict]:
        """Traduce texto a Cypher via LLM y ejecuta la consulta."""
        from pathlib import Path

        from app.llm.provider import Message

        prompt_path = (
            Path(__file__).parent.parent / "llm" / "prompts" / "graph_query.v1.md"
        )
        system = prompt_path.read_text(encoding="utf-8")

        filter_note = f"\nFiltrar por módulo: {module_filter}" if module_filter else ""
        user_content = f"Pregunta: {text}{filter_note}"

        messages = [Message(role="user", content=user_content)]
        try:
            raw = await llm.complete(system=system, messages=messages, max_tokens=512)
            cypher = _extract_cypher(raw)
            if not cypher:
                return [{"error": "No se pudo generar una consulta válida"}]
            return await self._repo.query_graph(cypher)
        except Exception as exc:
            log.warning("knowledge_query_failed", error=str(exc))
            return [{"error": str(exc)}]

    # ── RF-62: Sugerencias de regresión ──────────────────────────────────────

    async def get_regression_suggestions(
        self, cert_id: uuid.UUID, session: AsyncSession
    ) -> list[dict]:
        from app.certifications.models import Certification

        cert = await session.get(Certification, cert_id)
        if cert is None:
            return []

        keywords = cert.title.split() if cert.title else []
        return await self._repo.suggest_regression(cert.module, keywords)

    # ── RF-63: Glosario ───────────────────────────────────────────────────────

    async def upsert_term(self, name: str, definition: str, synonyms: list[str]) -> dict:
        await self._repo.upsert_term(name, definition, synonyms)
        return {"name": name, "definition": definition, "synonyms": synonyms}

    async def list_terms(self) -> list[dict]:
        return await self._repo.list_terms()

    async def delete_term(self, name: str) -> None:
        await self._repo.delete_term(name)

    async def get_terms_flat(self) -> list[dict]:
        """Retorna términos en formato plano para el linter (name + synonyms)."""
        return await self._repo.list_terms()


# ── Helpers de extracción ─────────────────────────────────────────────────────

def _extract_features(name: str, steps: list[str]) -> list[str]:
    features: list[str] = []
    text = name + " " + " ".join(steps)
    # Detectar módulos/pantallas mencionadas: "apartado de X", "módulo de X"
    for m in re.finditer(r"(?:apartado|módulo|sección|pantalla)\s+de\s+(\w[\w\s]+?)(?:\s+y|\s*,|\.|$)", text, re.IGNORECASE):
        feat = m.group(1).strip()
        if feat:
            features.append(feat[:100])
    return list(dict.fromkeys(features))[:5]


def _extract_rules(expected_result: str) -> list[str]:
    rules: list[str] = []
    # Fragmentos que parecen reglas: "el sistema debe", "el sistema valida", "no se permite"
    for m in re.finditer(
        r"(el\s+sistema\s+(?:debe|valida|rechaza|impide|muestra|verifica)[^.;]{0,120}[.;]?)",
        expected_result, re.IGNORECASE
    ):
        rules.append(m.group(1).strip()[:200])
    return rules[:3]


def _extract_messages(expected_result: str) -> list[str]:
    messages: list[str] = []
    # Texto entre comillas como mensajes de error
    for m in re.finditer(r'"([^"]{5,120})"', expected_result):
        messages.append(m.group(1))
    return messages[:3]


def _extract_cypher(raw: str) -> str:
    """Extrae la consulta Cypher del texto devuelto por el LLM."""
    # Buscar bloque ```cypher ... ```
    block = re.search(r"```(?:cypher)?\s*(MATCH[\s\S]*?)```", raw, re.IGNORECASE)
    if block:
        return block.group(1).strip()
    # Buscar MATCH directo
    match = re.search(r"(MATCH[\s\S]*?RETURN[^\n]+)", raw, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""

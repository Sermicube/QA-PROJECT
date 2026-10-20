"""Servicio de contexto de certificación (RF-10 a RF-14)."""
from __future__ import annotations

import uuid
from typing import Optional

from app.context.domain import ambiguity_rules, completeness
from app.context.models import AcceptanceCriterion, Ambiguity, ContextSource
from app.context.repository import ContextRepository
from app.core.storage import delete_file, save_upload
from app.llm.pii_guard import PIIGuard

_pii_guard = PIIGuard()


class ContextError(Exception):
    pass


class ContextService:
    def __init__(self, repo: ContextRepository) -> None:
        self._repo = repo

    # ── Descripción del analista (RF-10, RF-10a) ─────────────────────────────

    async def save_description(
        self, certification_id: uuid.UUID, cert_type: str, content: dict
    ) -> ContextSource:
        source = await self._repo.upsert_source(
            certification_id, "analyst_description", content=content
        )
        # Revisar completitud automáticamente y guardar hallazgos
        findings_raw = completeness.check_description(cert_type, content)
        await self._repo.replace_findings(
            certification_id,
            source.id,
            [{"field": f.field, "message": f.message} for f in findings_raw],
        )
        await self._repo.get_source(source.id)  # refrescar con findings
        return source

    # ── Documento de requerimiento (RF-10b, RF-11) ───────────────────────────

    async def save_document(
        self,
        certification_id: uuid.UUID,
        file_name: str,
        mime_type: str,
        data: bytes,
    ) -> ContextSource:
        from app.context.domain.extraction import extract_from_bytes

        if len(data) == 0:
            raise ContextError("El archivo está vacío")

        # Extraer texto y secciones
        extracted_text, sections = extract_from_bytes(data, mime_type, file_name)

        # Guardar archivo en disco
        file_path, stored_name = save_upload(certification_id, file_name, data)

        source = await self._repo.upsert_source(
            certification_id,
            "requirement_document",
            file_path=file_path,
            file_name=file_name,
            mime_type=mime_type,
            extracted_text=extracted_text,
            sections=[{"title": s.title, "content": s.content, "level": s.level} for s in sections],
        )
        return source

    # ── Reporte del incidente (RF-10c) ────────────────────────────────────────

    async def save_incident_report(
        self, certification_id: uuid.UUID, text: str
    ) -> ContextSource:
        source = await self._repo.upsert_source(
            certification_id,
            "incident_report",
            extracted_text=text,
        )
        return source

    # ── Eliminar fuente ───────────────────────────────────────────────────────

    async def delete_source(
        self, certification_id: uuid.UUID, source_id: uuid.UUID
    ) -> None:
        source = await self._repo.get_source(source_id)
        if source is None or source.certification_id != certification_id:
            raise ContextError("Fuente de contexto no encontrada")
        if source.file_path:
            delete_file(source.file_path)
        await self._repo.delete_source(source)

    # ── Listar fuentes ────────────────────────────────────────────────────────

    async def get_sources(self, certification_id: uuid.UUID) -> list[ContextSource]:
        return await self._repo.get_sources(certification_id)

    # ── Completitud (RF-10d) ──────────────────────────────────────────────────

    async def check_completeness(
        self, certification_id: uuid.UUID, cert_type: str
    ) -> list[dict]:
        sources = await self._repo.get_sources(certification_id)
        desc_source = next((s for s in sources if s.kind == "analyst_description"), None)
        if desc_source is None:
            return [{"field": "description", "message": "No se ha registrado ninguna descripción del analista."}]
        content = desc_source.content or {}
        findings = completeness.check_description(cert_type, content)
        # Persistir los hallazgos
        await self._repo.replace_findings(
            certification_id,
            desc_source.id,
            [{"field": f.field, "message": f.message} for f in findings],
        )
        return [{"field": f.field, "message": f.message} for f in findings]

    # ── Análisis local de ambigüedades (RF-13 — reglas locales) ─────────────

    # Category mapping for locally detected ambiguity types
    _LOCAL_CATEGORY: dict[str, str] = {
        "boundary_undefined": "changes_cases",
        "implicit_unit": "changes_cases",
        "vague_term": "other",
    }

    async def run_local_ambiguity_scan(self, certification_id: uuid.UUID) -> list[Ambiguity]:
        sources = await self._repo.get_sources(certification_id)
        if not sources:
            return []

        scan_inputs: list[dict] = []
        for src in sources:
            text = src.extracted_text or ""
            if src.kind == "analyst_description" and src.content:
                text = " ".join(str(v) for v in src.content.values() if v)
            scan_inputs.append({
                "kind": src.kind,
                "text": text,
                "sections": src.sections or [],
            })

        findings = ambiguity_rules.scan_sources(scan_inputs)

        # Clear ALL ambiguities (both local and semantic from previous runs).
        # Semantic ambiguities will be regenerated by _analyze step 7, preventing
        # duplicate accumulation on re-analysis.
        await self._repo.clear_ambiguities(certification_id)
        items: list[dict] = [
            {
                "type": f.type,
                "category": self._LOCAL_CATEGORY.get(f.type, "other"),
                "fragment": f.fragment,
                "location": f.location,
                "explanation": f.explanation,
                "question": f.question,
            }
            for f in findings
        ]
        return await self._repo.add_ambiguities(certification_id, items)

    # ── Criterios y ambigüedades ──────────────────────────────────────────────

    async def get_criteria(self, certification_id: uuid.UUID) -> list[AcceptanceCriterion]:
        return await self._repo.get_criteria(certification_id)

    async def get_ambiguities(self, certification_id: uuid.UUID) -> list[Ambiguity]:
        return await self._repo.get_ambiguities(certification_id)

    async def resolve_ambiguity(
        self, certification_id: uuid.UUID, ambiguity_id: uuid.UUID, resolution: str, resolved_by: str
    ) -> Ambiguity:
        amb = await self._repo.resolve_ambiguity(ambiguity_id, resolution, resolved_by)
        if amb is None or amb.certification_id != certification_id:
            raise ContextError("Ambigüedad no encontrada")
        return amb

    # ── Propuesta de descripción estructurada (RF-11) ────────────────────────

    async def propose_description(
        self, free_text: str, cert_type: str, user_id: str | None = None
    ) -> dict[str, str]:
        """Usa el LLM para extraer campos estructurados a partir del texto libre."""
        import json
        import re
        from pathlib import Path

        from app.llm.factory import get_provider, get_provider_for_user
        from app.llm.provider import Message

        if len(free_text.strip()) < 20:
            raise ContextError("El texto libre es muy corto para extraer campos estructurados.")

        masked, _ = _pii_guard.mask(free_text)

        llm = await get_provider_for_user(user_id) if user_id else get_provider()

        prompt_path = (
            Path(__file__).parent.parent / "llm" / "prompts" / "propose_description.v1.md"
        )
        system = prompt_path.read_text(encoding="utf-8")
        messages = [Message(role="user", content=f"tipo: {cert_type}\n\ntexto libre:\n{masked}")]

        try:
            raw = await llm.complete(system=system, messages=messages, max_tokens=512)
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return {k: str(v) for k, v in parsed.items() if isinstance(v, (str, type(None)))}
        except Exception:
            pass
        return {}

    def _build_context_text(self, sources: list[ContextSource]) -> str:
        """Construye texto del contexto para enviar al LLM (sin PII)."""
        parts: list[str] = []
        for src in sources:
            if src.kind == "analyst_description" and src.content:
                text = "\n".join(f"{k}: {v}" for k, v in src.content.items() if v)
            elif src.extracted_text:
                text = src.extracted_text
            else:
                continue
            masked, _ = _pii_guard.mask(text)
            parts.append(f"[{src.kind}]\n{masked}")
        return "\n\n".join(parts)

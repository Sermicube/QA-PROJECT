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
        # Reemplazar ambigüedades locales (tipo ≠ missing_branch, ≠ contradiction, ≠ incomplete_context)
        existing = await self._repo.get_ambiguities(certification_id)
        local_types = {"boundary_undefined", "implicit_unit", "vague_term"}
        non_local = [a for a in existing if a.type not in local_types]

        # Borrar solo las locales anteriores
        await self._repo.clear_ambiguities(certification_id)
        all_items: list[dict] = [
            {
                "type": a.type,
                "fragment": a.fragment,
                "location": a.location,
                "explanation": a.explanation,
                "question": a.question,
            }
            for a in non_local
        ]
        all_items.extend(
            {
                "type": f.type,
                "fragment": f.fragment,
                "location": f.location,
                "explanation": f.explanation,
                "question": f.question,
            }
            for f in findings
        )
        return await self._repo.add_ambiguities(certification_id, all_items)

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

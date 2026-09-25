"""Servicio de casos de prueba (RF-15 a RF-19)."""
from __future__ import annotations

import uuid
from typing import Optional

from app.context.repository import ContextRepository
from app.testcases.domain.linter import CaseInput, LintIssue, lint_batch, lint_case
from app.testcases.models import TestCase
from app.testcases.repository import TestCaseRepository
from app.testcases.schemas import TraceabilityRow


class TestCaseError(Exception):
    pass


class TestCaseService:
    def __init__(self, repo: TestCaseRepository, ctx_repo: ContextRepository) -> None:
        self._repo = repo
        self._ctx = ctx_repo

    # ── Crear caso (RF-18) ─────────────────────────────────────────────────────

    async def create(
        self,
        certification_id: uuid.UUID,
        name: str,
        preconditions: list[str],
        steps: list[str],
        expected_result: str,
        criteria_ids: list[str],
        boundary: Optional[str] = None,
        order: int = 0,
    ) -> TestCase:
        code = await self._repo.next_code(certification_id)
        tc = await self._repo.create(
            certification_id=certification_id,
            code=code,
            name=name,
            preconditions=preconditions,
            steps=steps,
            expected_result=expected_result,
            boundary=boundary,
            order=order,
        )
        # Resolver criterion_ids (string CA-XX) a UUIDs
        crit_uuids = await self._resolve_criterion_ids(certification_id, criteria_ids)
        await self._repo.link_criteria(tc.id, crit_uuids)
        return await self._repo.commit_and_refresh(tc)

    # ── Listar / obtener ───────────────────────────────────────────────────────

    async def list(self, certification_id: uuid.UUID) -> list[TestCase]:
        return await self._repo.list_by_cert(certification_id)

    async def get(self, test_case_id: uuid.UUID, certification_id: uuid.UUID) -> TestCase:
        tc = await self._repo.get(test_case_id)
        if tc is None or tc.certification_id != certification_id:
            raise TestCaseError("Caso de prueba no encontrado")
        return tc

    # ── Actualizar (RF-18) ─────────────────────────────────────────────────────

    async def update(
        self,
        test_case_id: uuid.UUID,
        certification_id: uuid.UUID,
        **kwargs: object,
    ) -> TestCase:
        tc = await self.get(test_case_id, certification_id)
        criteria_ids = kwargs.pop("criteria_ids", None)
        if criteria_ids is not None:
            crit_uuids = await self._resolve_criterion_ids(certification_id, criteria_ids)
            await self._repo.link_criteria(tc.id, crit_uuids)
        return await self._repo.update(tc, **kwargs)

    # ── Eliminar (RF-18) ───────────────────────────────────────────────────────

    async def delete(self, test_case_id: uuid.UUID, certification_id: uuid.UUID) -> None:
        tc = await self.get(test_case_id, certification_id)
        await self._repo.delete(tc)

    # ── Linter (RF-17) ────────────────────────────────────────────────────────

    async def lint(self, test_case_id: uuid.UUID, certification_id: uuid.UUID) -> list[LintIssue]:
        """Corre el linter sobre un caso individual."""
        tc = await self.get(test_case_id, certification_id)
        case_input = await self._to_input(tc, certification_id)
        issues = lint_case(case_input)
        # Persistir resultados del linter en el caso
        await self._repo.update(tc, lint_results=[
            {"code": i.code, "message": i.message, "severity": i.severity} for i in issues
        ])
        return issues

    async def lint_all(self, certification_id: uuid.UUID) -> dict[str, list[LintIssue]]:
        """Corre el linter sobre todos los casos de la certificación (incluye L07, L08)."""
        cases = await self._repo.list_by_cert(certification_id)
        criteria = await self._ctx.get_criteria(certification_id)
        criterion_codes = [c.code for c in criteria]

        inputs = [await self._to_input(tc, certification_id) for tc in cases]
        results = lint_batch(inputs, criterion_codes)

        for tc in cases:
            issues = results.get(tc.code, [])
            await self._repo.update(tc, lint_results=[
                {"code": i.code, "message": i.message, "severity": i.severity} for i in issues
            ])
        return results

    # ── Aprobar (RF-18) ────────────────────────────────────────────────────────

    async def approve(self, test_case_id: uuid.UUID, certification_id: uuid.UUID) -> TestCase:
        tc = await self.get(test_case_id, certification_id)
        # Correr linter antes de aprobar
        case_input = await self._to_input(tc, certification_id)
        issues = lint_case(case_input)
        errors = [i for i in issues if i.severity == "error"]
        if errors:
            raise TestCaseError(
                f"El caso tiene {len(errors)} error(es) de linter. Corrígelos antes de aprobar."
            )
        return await self._repo.update(tc, status="approved")

    # ── Matriz de trazabilidad (RF-19) ────────────────────────────────────────

    async def traceability(self, certification_id: uuid.UUID) -> list[TraceabilityRow]:
        criteria = await self._ctx.get_criteria(certification_id)
        cases = await self._repo.list_by_cert(certification_id)

        # Construir mapa criterion_id → case_codes
        coverage: dict[uuid.UUID, list[str]] = {c.id: [] for c in criteria}
        for tc in cases:
            links = await self._repo.get_criterion_links(tc.id)
            for cid in links:
                if cid in coverage:
                    coverage[cid].append(tc.code)

        return [
            TraceabilityRow(
                criterion_code=c.code,
                criterion_text=c.text,
                case_codes=coverage[c.id],
                covered=len(coverage[c.id]) > 0,
            )
            for c in criteria
        ]

    # ── Importar casos (RF-16) ────────────────────────────────────────────────

    async def import_cases(
        self, certification_id: uuid.UUID, cases_data: list[dict]
    ) -> list[TestCase]:
        result = []
        for data in cases_data:
            tc = await self.create(
                certification_id=certification_id,
                name=data["name"],
                preconditions=data.get("preconditions", []),
                steps=data.get("steps", []),
                expected_result=data["expected_result"],
                criteria_ids=data.get("criteria_ids", []),
                boundary=data.get("boundary"),
                order=data.get("order", 0),
            )
            result.append(tc)
        return result

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _to_input(self, tc: TestCase, certification_id: uuid.UUID) -> CaseInput:
        links = await self._repo.get_criterion_links(tc.id)
        # Convertir UUIDs a códigos CA-XX
        criteria = await self._ctx.get_criteria(certification_id)
        id_to_code = {c.id: c.code for c in criteria}
        criteria_codes = [id_to_code.get(cid, str(cid)) for cid in links]

        return CaseInput(
            code=tc.code,
            name=tc.name,
            preconditions=list(tc.preconditions or []),
            steps=list(tc.steps or []),
            expected_result=tc.expected_result,
            boundary=tc.boundary,
            criteria_ids=criteria_codes,
        )

    async def _resolve_criterion_ids(
        self, certification_id: uuid.UUID, codes: list[str]
    ) -> list[uuid.UUID]:
        if not codes:
            return []
        criteria = await self._ctx.get_criteria(certification_id)
        code_to_id = {c.code: c.id for c in criteria}
        return [code_to_id[code] for code in codes if code in code_to_id]

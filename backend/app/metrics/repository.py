"""Acceso a datos del módulo metrics."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics.models import BaselineCertification, LlmCall, ReworkEvent


class MetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── ReworkEvent ───────────────────────────────────────────────────────────

    async def add_rework(
        self,
        cert_id: uuid.UUID,
        tc_id: uuid.UUID | None,
        reason: str,
    ) -> ReworkEvent:
        ev = ReworkEvent(
            certification_id=cert_id,
            test_case_id=tc_id,
            reason=reason,
            reported_at=datetime.now(timezone.utc),
        )
        self._s.add(ev)
        await self._s.flush()
        return ev

    async def list_rework(self, cert_id: uuid.UUID) -> list[ReworkEvent]:
        result = await self._s.execute(
            select(ReworkEvent)
            .where(ReworkEvent.certification_id == cert_id)
            .order_by(ReworkEvent.reported_at)
        )
        return list(result.scalars().all())

    # ── BaselineCertification ─────────────────────────────────────────────────

    async def add_baseline(
        self,
        owner_id: uuid.UUID,
        type: str,
        module: str,
        duration_minutes: int,
        cert_date: date,
        notes: str | None,
    ) -> BaselineCertification:
        b = BaselineCertification(
            owner_id=owner_id,
            type=type,
            module=module,
            duration_minutes=duration_minutes,
            date=cert_date,
            notes=notes,
        )
        self._s.add(b)
        await self._s.flush()
        return b

    async def list_baselines(self, owner_id: uuid.UUID) -> list[BaselineCertification]:
        result = await self._s.execute(
            select(BaselineCertification)
            .where(BaselineCertification.owner_id == owner_id)
            .order_by(BaselineCertification.date.desc())
        )
        return list(result.scalars().all())

    # ── LlmCall ───────────────────────────────────────────────────────────────

    async def add_llm_call(
        self,
        module: str,
        prompt_name: str,
        prompt_version: str,
        provider: str,
        tokens_in: int,
        tokens_out: int,
        duration_ms: int,
        success: bool,
    ) -> LlmCall:
        call = LlmCall(
            module=module,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            provider=provider,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_ms=duration_ms,
            success=success,
        )
        self._s.add(call)
        await self._s.flush()
        return call

    # ── Summary ───────────────────────────────────────────────────────────────

    async def summary(self, owner_id: uuid.UUID) -> dict:
        from app.certifications.models import Certification, StageEvent

        # Certificaciones propias con duración (diferencia entre primer y último stage_event)
        certs_result = await self._s.execute(
            select(Certification).where(
                Certification.owner_id == owner_id,
                Certification.status == "active",
            )
        )
        certs = list(certs_result.scalars().all())

        # Agrupar por tipo y módulo
        from collections import defaultdict
        groups: dict[tuple[str, str], list[float]] = defaultdict(list)

        for cert in certs:
            if cert.closed_at and cert.created_at:
                delta = (cert.closed_at - cert.created_at).total_seconds() / 60
                groups[(cert.type, cert.module)].append(delta)

        # Devoluciones totales
        rework_result = await self._s.execute(
            select(func.count(ReworkEvent.id)).select_from(ReworkEvent)
            .join(Certification, Certification.id == ReworkEvent.certification_id)
            .where(Certification.owner_id == owner_id)
        )
        total_rework = rework_result.scalar() or 0

        # Línea base
        baselines = await self.list_baselines(owner_id)
        baseline_minutes = [b.duration_minutes for b in baselines]
        baseline_avg = sum(baseline_minutes) / len(baseline_minutes) if baseline_minutes else None

        # Construir por módulo
        by_module = []
        all_durations: list[float] = []
        for (type_, module), durations in groups.items():
            all_durations.extend(durations)
            # Devoluciones de este módulo
            module_rework_result = await self._s.execute(
                select(func.count(ReworkEvent.id)).select_from(ReworkEvent)
                .join(Certification, Certification.id == ReworkEvent.certification_id)
                .where(
                    Certification.owner_id == owner_id,
                    Certification.type == type_,
                    Certification.module == module,
                )
            )
            module_rework = module_rework_result.scalar() or 0

            module_baseline = [
                b.duration_minutes for b in baselines
                if b.type == type_ and b.module == module
            ]
            by_module.append({
                "type": type_,
                "module": module,
                "avg_duration_minutes": sum(durations) / len(durations) if durations else None,
                "baseline_avg_minutes": sum(module_baseline) / len(module_baseline) if module_baseline else None,
                "total_certifications": len(durations),
                "total_rework": module_rework,
            })

        return {
            "by_module": by_module,
            "total_certifications": len(certs),
            "total_rework": total_rework,
            "overall_avg_minutes": sum(all_durations) / len(all_durations) if all_durations else None,
            "baseline_avg_minutes": baseline_avg,
        }

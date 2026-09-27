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

    # ── RF-53: advanced aggregations ─────────────────────────────────────────

    async def by_type(self, owner_id: uuid.UUID) -> list[dict]:
        from app.certifications.models import Certification
        result = await self._s.execute(
            select(Certification).where(
                Certification.owner_id == owner_id,
                Certification.stage == "closed",
            )
        )
        certs = list(result.scalars().all())
        groups: dict[str, list[float]] = {}
        for c in certs:
            if c.closed_at and c.created_at:
                mins = (c.closed_at - c.created_at).total_seconds() / 60
                groups.setdefault(c.type, []).append(mins)

        rework_res = await self._s.execute(
            select(ReworkEvent.certification_id, func.count(ReworkEvent.id))
            .join(Certification, Certification.id == ReworkEvent.certification_id)
            .where(Certification.owner_id == owner_id)
            .group_by(ReworkEvent.certification_id)
        )
        cert_rework: dict[uuid.UUID, int] = {r[0]: r[1] for r in rework_res}

        type_rework: dict[str, int] = {}
        for c in certs:
            type_rework[c.type] = type_rework.get(c.type, 0) + cert_rework.get(c.id, 0)

        out = []
        for t, durations in groups.items():
            out.append({
                "type": t,
                "total": len(durations),
                "avg_minutes": sum(durations) / len(durations) if durations else None,
                "total_rework": type_rework.get(t, 0),
            })
        return sorted(out, key=lambda x: x["total"], reverse=True)

    async def by_module(self, owner_id: uuid.UUID) -> list[dict]:
        from app.certifications.models import Certification
        result = await self._s.execute(
            select(Certification).where(
                Certification.owner_id == owner_id,
                Certification.stage == "closed",
            )
        )
        certs = list(result.scalars().all())
        groups: dict[str, list[float]] = {}
        rework_by_module: dict[str, int] = {}
        for c in certs:
            if c.closed_at and c.created_at:
                mins = (c.closed_at - c.created_at).total_seconds() / 60
                groups.setdefault(c.module, []).append(mins)

        rework_res = await self._s.execute(
            select(Certification.module, func.count(ReworkEvent.id))
            .join(ReworkEvent, ReworkEvent.certification_id == Certification.id, isouter=True)
            .where(Certification.owner_id == owner_id, Certification.stage == "closed")
            .group_by(Certification.module)
        )
        rework_by_module = {r[0]: r[1] for r in rework_res}

        out = []
        for module, durations in groups.items():
            out.append({
                "module": module,
                "total": len(durations),
                "avg_minutes": sum(durations) / len(durations) if durations else None,
                "total_rework": rework_by_module.get(module, 0),
            })
        return sorted(out, key=lambda x: (x["avg_minutes"] or 0), reverse=True)

    async def baseline_comparison(self, owner_id: uuid.UUID) -> list[dict]:
        from app.certifications.models import Certification
        result = await self._s.execute(
            select(Certification).where(
                Certification.owner_id == owner_id,
                Certification.stage == "closed",
            )
        )
        certs = list(result.scalars().all())
        tool_by_module: dict[str, list[float]] = {}
        for c in certs:
            if c.closed_at and c.created_at:
                mins = (c.closed_at - c.created_at).total_seconds() / 60
                tool_by_module.setdefault(c.module, []).append(mins)

        baselines = await self.list_baselines(owner_id)
        base_by_module: dict[str, list[int]] = {}
        for b in baselines:
            base_by_module.setdefault(b.module, []).append(b.duration_minutes)

        all_modules = set(tool_by_module.keys()) | set(base_by_module.keys())
        out = []
        for module in sorted(all_modules):
            tool_vals = tool_by_module.get(module, [])
            base_vals = base_by_module.get(module, [])
            tool_avg = sum(tool_vals) / len(tool_vals) if tool_vals else None
            base_avg = sum(base_vals) / len(base_vals) if base_vals else None
            if tool_avg is not None and base_avg is not None and base_avg > 0:
                delta_pct = (tool_avg - base_avg) / base_avg * 100
            else:
                delta_pct = None
            out.append({
                "module": module,
                "with_tool_avg": tool_avg,
                "baseline_avg": base_avg,
                "delta_pct": delta_pct,
            })
        return out

    async def export_data(self, owner_id: uuid.UUID) -> list[dict]:
        from app.certifications.models import Certification
        result = await self._s.execute(
            select(Certification).where(
                Certification.owner_id == owner_id,
                Certification.stage == "closed",
            ).order_by(Certification.closed_at.desc())
        )
        certs = list(result.scalars().all())
        rows = []
        for c in certs:
            total_mins: float | None = None
            if c.closed_at and c.created_at:
                total_mins = (c.closed_at - c.created_at).total_seconds() / 60
            rows.append({
                "external_code": c.external_code,
                "title": c.title,
                "type": c.type,
                "module": c.module,
                "closed_at": c.closed_at.isoformat() if c.closed_at else "",
                "total_minutes": round(total_mins, 1) if total_mins is not None else None,
            })
        return rows

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

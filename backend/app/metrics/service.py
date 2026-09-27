"""Lógica de negocio del módulo metrics (RF-50 a RF-52)."""
from __future__ import annotations

import uuid
from datetime import date

from app.metrics.models import BaselineCertification, ReworkEvent
from app.metrics.repository import MetricsRepository
from app.metrics.schemas import (
    BaselineComparisonItem,
    BaselineComparisonOut,
    ByModuleOut,
    ByTypeOut,
    MetricsSummaryOut,
    ModuleMetrics,
    ModuleMetricsOut,
    TypeMetrics,
)


class MetricsService:
    def __init__(self, repo: MetricsRepository) -> None:
        self._repo = repo

    async def add_rework(
        self,
        cert_id: uuid.UUID,
        tc_id: uuid.UUID | None,
        reason: str,
    ) -> ReworkEvent:
        return await self._repo.add_rework(cert_id, tc_id, reason)

    async def list_rework(self, cert_id: uuid.UUID) -> list[ReworkEvent]:
        return await self._repo.list_rework(cert_id)

    async def add_baseline(
        self,
        owner_id: uuid.UUID,
        type: str,
        module: str,
        duration_minutes: int,
        cert_date: date,
        notes: str | None,
    ) -> BaselineCertification:
        return await self._repo.add_baseline(
            owner_id, type, module, duration_minutes, cert_date, notes
        )

    async def list_baselines(self, owner_id: uuid.UUID) -> list[BaselineCertification]:
        return await self._repo.list_baselines(owner_id)

    async def by_type(self, owner_id: uuid.UUID) -> ByTypeOut:
        items = await self._repo.by_type(owner_id)
        return ByTypeOut(items=[TypeMetrics(**i) for i in items])

    async def by_module(self, owner_id: uuid.UUID) -> ByModuleOut:
        items = await self._repo.by_module(owner_id)
        return ByModuleOut(items=[ModuleMetricsOut(**i) for i in items])

    async def baseline_comparison(self, owner_id: uuid.UUID) -> BaselineComparisonOut:
        items = await self._repo.baseline_comparison(owner_id)
        return BaselineComparisonOut(items=[BaselineComparisonItem(**i) for i in items])

    async def export_data(self, owner_id: uuid.UUID) -> list[dict]:
        return await self._repo.export_data(owner_id)

    async def summary(self, owner_id: uuid.UUID) -> MetricsSummaryOut:
        data = await self._repo.summary(owner_id)
        return MetricsSummaryOut(
            by_module=[ModuleMetrics(**m) for m in data["by_module"]],
            total_certifications=data["total_certifications"],
            total_rework=data["total_rework"],
            overall_avg_minutes=data["overall_avg_minutes"],
            baseline_avg_minutes=data["baseline_avg_minutes"],
        )

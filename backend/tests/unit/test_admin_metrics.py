"""Tests para admin endpoints y métricas avanzadas (RF-53)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from app.users.router import require_admin
from app.users.models import User


# ── Admin tests ───────────────────────────────────────────────────────────────

def _make_user(role: str = "analyst") -> User:
    u = MagicMock(spec=User)
    u.role = role
    return u


def test_require_admin_raises_for_analyst():
    user = _make_user("analyst")
    with pytest.raises(HTTPException) as exc_info:
        require_admin(current_user=user)
    assert exc_info.value.status_code == 403


def test_require_admin_raises_for_lead():
    user = _make_user("lead")
    with pytest.raises(HTTPException) as exc_info:
        require_admin(current_user=user)
    assert exc_info.value.status_code == 403


def test_require_admin_passes_for_admin():
    user = _make_user("admin")
    result = require_admin(current_user=user)
    assert result is user


# ── Metrics RF-53 tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_metrics_by_type_empty():
    from app.metrics.service import MetricsService
    import uuid

    repo = MagicMock()
    repo.by_type = AsyncMock(return_value=[])
    svc = MetricsService(repo)
    result = await svc.by_type(uuid.uuid4())
    assert result.items == []


@pytest.mark.asyncio
async def test_metrics_by_module_groups():
    from app.metrics.service import MetricsService
    import uuid

    repo = MagicMock()
    repo.by_module = AsyncMock(return_value=[
        {"module": "Novedades", "total": 3, "avg_minutes": 45.0, "total_rework": 1},
        {"module": "Contratos", "total": 1, "avg_minutes": 90.0, "total_rework": 0},
    ])
    svc = MetricsService(repo)
    result = await svc.by_module(uuid.uuid4())
    assert len(result.items) == 2
    assert result.items[0].module == "Novedades"
    assert result.items[0].total == 3


@pytest.mark.asyncio
async def test_metrics_baseline_comparison_no_data():
    from app.metrics.service import MetricsService
    import uuid

    repo = MagicMock()
    repo.baseline_comparison = AsyncMock(return_value=[])
    svc = MetricsService(repo)
    result = await svc.baseline_comparison(uuid.uuid4())
    assert result.items == []


@pytest.mark.asyncio
async def test_metrics_baseline_comparison_delta():
    from app.metrics.service import MetricsService
    import uuid

    repo = MagicMock()
    repo.baseline_comparison = AsyncMock(return_value=[
        {
            "module": "Novedades",
            "with_tool_avg": 60.0,
            "baseline_avg": 120.0,
            "delta_pct": -50.0,
        }
    ])
    svc = MetricsService(repo)
    result = await svc.baseline_comparison(uuid.uuid4())
    assert result.items[0].delta_pct == pytest.approx(-50.0)
    assert result.items[0].with_tool_avg < result.items[0].baseline_avg  # improvement

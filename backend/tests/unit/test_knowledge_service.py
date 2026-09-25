"""Tests del módulo knowledge (RF-60 a RF-63)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.knowledge.repository import KnowledgeRepository
from app.knowledge.service import KnowledgeService, _extract_features, _extract_rules


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _repo(driver=None) -> KnowledgeRepository:
    return KnowledgeRepository(driver)


def _svc(driver=None) -> KnowledgeService:
    return KnowledgeService(_repo(driver))


# ── RF-60: ingestar certificación ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_no_driver_skips_gracefully():
    """Si driver=None (NEO4J_ENABLED=False), ingest no falla."""
    svc = _svc(driver=None)
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    result = await svc.ingest_certification(
        __import__("uuid").uuid4(), session
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_record_cert_calls_write():
    """record_certification llama execute_write con un driver mock."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.execute_write = AsyncMock()

    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)

    repo = _repo(mock_driver)
    await repo.record_certification({
        "cert_id": "test-id",
        "title": "Test",
        "type": "bug",
        "module": "Afiliación",
        "cases": [],
    })
    mock_session.execute_write.assert_called_once()


# ── RF-62: sugerencias de regresión ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_suggest_regression_returns_list():
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[
        {"cert_id": "c1", "cert_title": "T", "tc_id": "t1", "tc_name": "Validar", "tc_result": "passed"},
    ])
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)

    repo = _repo(mock_driver)
    results = await repo.suggest_regression("Afiliación", ["exclusión"])
    assert isinstance(results, list)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_suggest_regression_no_driver_returns_empty():
    repo = _repo(None)
    results = await repo.suggest_regression("Afiliación", [])
    assert results == []


# ── RF-63: glosario ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_and_list_terms():
    """upsert_term llama execute_write; list_terms devuelve lista."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.execute_write = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[
        {"name": "exclusión", "definition": "Exclusión de beneficiario", "synonyms": ["desvinculación"]},
    ])
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)

    repo = _repo(mock_driver)
    await repo.upsert_term("exclusión", "Exclusión de beneficiario", ["desvinculación"])
    mock_session.execute_write.assert_called_once()

    terms = await repo.list_terms()
    assert len(terms) == 1
    assert terms[0]["name"] == "exclusión"


@pytest.mark.asyncio
async def test_list_terms_no_driver_returns_empty():
    repo = _repo(None)
    assert await repo.list_terms() == []


# ── helpers ───────────────────────────────────────────────────────────────────

def test_extract_features_empty():
    assert _extract_features("Validar que el sistema genere novedad", []) == []


def test_extract_features_with_apartado():
    features = _extract_features(
        "Validar",
        ["Se accede al apartado de Novedades de afiliación y se genera"],
    )
    assert len(features) >= 1
    assert "Novedades de afiliación" in features[0]


def test_extract_rules_basic():
    rules = _extract_rules("El sistema debe mostrar el mensaje de error. El sistema valida la fecha.")
    assert len(rules) >= 1

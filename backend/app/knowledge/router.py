"""Endpoints del Mapa Vivo (RF-60 a RF-63)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.neo4j_client import get_driver
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.schemas import (
    KnowledgeQueryIn,
    KnowledgeQueryOut,
    RegressionSuggestion,
    TermIn,
    TermOut,
)
from app.knowledge.service import KnowledgeService
from app.users.models import User
from app.users.router import get_current_user

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


def _svc() -> KnowledgeService:
    return KnowledgeService(KnowledgeRepository(get_driver()))


# ── RF-62: Sugerencias de regresión ──────────────────────────────────────────

@router.get(
    "/certifications/{cert_id}/regression",
    response_model=list[RegressionSuggestion],
)
async def regression_suggestions(
    cert_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    svc: KnowledgeService = Depends(_svc),
    session: AsyncSession = Depends(get_db),
) -> list[RegressionSuggestion]:
    results = await svc.get_regression_suggestions(cert_id, session)
    return [RegressionSuggestion(**r) for r in results if all(k in r for k in RegressionSuggestion.model_fields)]


# ── RF-61: Consulta en lenguaje natural ──────────────────────────────────────

@router.post("/query", response_model=KnowledgeQueryOut)
async def query_graph(
    body: KnowledgeQueryIn,
    current_user: User = Depends(get_current_user),
    svc: KnowledgeService = Depends(_svc),
) -> KnowledgeQueryOut:
    from app.llm.factory import get_provider_for_user
    llm = await get_provider_for_user(current_user.id)
    results = await svc.natural_language_query(body.text, body.module_filter, llm)
    return KnowledgeQueryOut(results=results)


# ── RF-63: Glosario ───────────────────────────────────────────────────────────

@router.get("/glossary", response_model=list[TermOut])
async def list_glossary(
    _user: User = Depends(get_current_user),
    svc: KnowledgeService = Depends(_svc),
) -> list[TermOut]:
    terms = await svc.list_terms()
    return [TermOut(**t) for t in terms]


@router.post("/glossary", response_model=TermOut, status_code=status.HTTP_201_CREATED)
async def create_term(
    body: TermIn,
    _user: User = Depends(get_current_user),
    svc: KnowledgeService = Depends(_svc),
) -> TermOut:
    result = await svc.upsert_term(body.name, body.definition, body.synonyms)
    return TermOut(**result)


@router.put("/glossary/{name}", response_model=TermOut)
async def update_term(
    name: str,
    body: TermIn,
    _user: User = Depends(get_current_user),
    svc: KnowledgeService = Depends(_svc),
) -> TermOut:
    result = await svc.upsert_term(body.name or name, body.definition, body.synonyms)
    return TermOut(**result)


@router.delete("/glossary/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_term(
    name: str,
    _user: User = Depends(get_current_user),
    svc: KnowledgeService = Depends(_svc),
) -> None:
    await svc.delete_term(name)

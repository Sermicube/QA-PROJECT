from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.recipes.repository import RecipeRepository
from app.recipes.schemas import (
    CasePatternRead,
    CaseStyleRead,
    InconclusiveReasonRead,
    InconclusiveReasonToggle,
    RecipeRead,
)
from app.recipes.service import RecipeError, RecipeService
from app.users.models import User
from app.users.router import get_current_user

router = APIRouter(prefix="/api/v1", tags=["recipes"])


def _svc(session: AsyncSession = Depends(get_db)) -> RecipeService:
    return RecipeService(RecipeRepository(session))


@router.get("/recipes", response_model=list[RecipeRead])
async def list_recipes(svc: RecipeService = Depends(_svc)) -> list[RecipeRead]:
    items = await svc.list_recipes()
    return [RecipeRead.model_validate(r) for r in items]


@router.get("/recipes/{code}", response_model=RecipeRead)
async def get_recipe(code: str, svc: RecipeService = Depends(_svc)) -> RecipeRead:
    try:
        r = await svc.get_recipe(code)
    except RecipeError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
    return RecipeRead.model_validate(r)


@router.get("/case-styles", response_model=list[CaseStyleRead])
async def list_case_styles(svc: RecipeService = Depends(_svc)) -> list[CaseStyleRead]:
    items = await svc.list_case_styles()
    return [CaseStyleRead.model_validate(s) for s in items]


@router.get("/case-patterns", response_model=list[CasePatternRead])
async def list_case_patterns(svc: RecipeService = Depends(_svc)) -> list[CasePatternRead]:
    items = await svc.list_case_patterns()
    return [CasePatternRead.model_validate(p) for p in items]


@router.get("/inconclusive-reasons", response_model=list[InconclusiveReasonRead])
async def list_inconclusive_reasons(
    svc: RecipeService = Depends(_svc),
    current_user: User = Depends(get_current_user),
) -> list[InconclusiveReasonRead]:
    active_only = current_user.role not in ("lead", "admin")
    items = await svc.list_inconclusive_reasons(active_only=active_only)
    return [InconclusiveReasonRead.model_validate(r) for r in items]


@router.patch("/inconclusive-reasons/{code}", response_model=InconclusiveReasonRead)
async def toggle_inconclusive_reason(
    code: str,
    body: InconclusiveReasonToggle,
    svc: RecipeService = Depends(_svc),
    current_user: User = Depends(get_current_user),
) -> InconclusiveReasonRead:
    if current_user.role not in ("lead", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso")
    try:
        r = await svc.toggle_inconclusive_reason(code, body.is_active)
    except RecipeError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub-razón no encontrada")
    return InconclusiveReasonRead.model_validate(r)

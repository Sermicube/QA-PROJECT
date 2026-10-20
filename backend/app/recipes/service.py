import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.recipes.models import CasePattern, CaseStyle, InconclusiveReason, Recipe
from app.recipes.repository import RecipeRepository
from app.recipes import seed as _seed

log = structlog.get_logger()


class RecipeError(Exception):
    pass


class RecipeService:
    def __init__(self, repo: RecipeRepository) -> None:
        self._repo = repo

    async def list_recipes(self) -> list[Recipe]:
        return await self._repo.list_recipes()

    async def get_recipe(self, code: str) -> Recipe:
        r = await self._repo.get_recipe_by_code(code)
        if r is None:
            raise RecipeError(f"Receta no encontrada: {code}")
        return r

    async def list_case_styles(self) -> list[CaseStyle]:
        return await self._repo.list_case_styles()

    async def list_case_patterns(self) -> list[CasePattern]:
        return await self._repo.list_case_patterns()

    async def list_inconclusive_reasons(self, *, active_only: bool = True) -> list[InconclusiveReason]:
        return await self._repo.list_inconclusive_reasons(active_only=active_only)

    async def toggle_inconclusive_reason(self, code: str, is_active: bool) -> InconclusiveReason:
        reason = await self._repo.get_inconclusive_reason(code)
        if reason is None:
            raise RecipeError(f"Sub-razón no encontrada: {code}")
        reason.is_active = is_active
        await self._repo._s.flush()
        await self._repo._s.commit()
        await self._repo._s.refresh(reason)
        return reason


async def seed_all(session: AsyncSession) -> None:
    """Insert builtin seed data only if each record does not already exist.

    Idempotent: safe to call on every startup. Never overwrites records that
    a lead may have edited (labels, is_active, etc.).
    """
    repo = RecipeRepository(session)
    for data in _seed.RECIPES:
        await repo.insert_recipe_if_absent(data)
    for data in _seed.CASE_STYLES:
        await repo.insert_case_style_if_absent(data)
    for data in _seed.CASE_PATTERNS:
        await repo.insert_case_pattern_if_absent(data)
    for data in _seed.INCONCLUSIVE_REASONS:
        await repo.insert_inconclusive_reason_if_absent(data)
    await session.commit()
    log.info("recipes_seed_complete")

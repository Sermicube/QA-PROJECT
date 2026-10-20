from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.recipes.models import CasePattern, CaseStyle, InconclusiveReason, Recipe


class RecipeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_recipe_by_code(self, code: str) -> Optional[Recipe]:
        r = await self._s.execute(select(Recipe).where(Recipe.code == code))
        return r.scalar_one_or_none()

    async def list_recipes(self) -> list[Recipe]:
        r = await self._s.execute(select(Recipe).order_by(Recipe.name))
        return list(r.scalars().all())

    async def insert_recipe_if_absent(self, data: dict) -> Recipe:
        """Insert only if the code does not exist yet. Never overwrites."""
        existing = await self.get_recipe_by_code(data["code"])
        if existing is not None:
            return existing
        obj = Recipe(**data)
        self._s.add(obj)
        await self._s.flush()
        return obj

    async def get_case_style_by_code(self, code: str) -> Optional[CaseStyle]:
        r = await self._s.execute(select(CaseStyle).where(CaseStyle.code == code))
        return r.scalar_one_or_none()

    async def list_case_styles(self) -> list[CaseStyle]:
        r = await self._s.execute(select(CaseStyle).order_by(CaseStyle.name))
        return list(r.scalars().all())

    async def insert_case_style_if_absent(self, data: dict) -> CaseStyle:
        existing = await self.get_case_style_by_code(data["code"])
        if existing is not None:
            return existing
        obj = CaseStyle(**data)
        self._s.add(obj)
        await self._s.flush()
        return obj

    async def list_case_patterns(self) -> list[CasePattern]:
        r = await self._s.execute(select(CasePattern).order_by(CasePattern.name))
        return list(r.scalars().all())

    async def insert_case_pattern_if_absent(self, data: dict) -> CasePattern:
        r = await self._s.execute(select(CasePattern).where(CasePattern.code == data["code"]))
        existing = r.scalar_one_or_none()
        if existing is not None:
            return existing
        obj = CasePattern(**data)
        self._s.add(obj)
        await self._s.flush()
        return obj

    async def list_inconclusive_reasons(self, *, active_only: bool = False) -> list[InconclusiveReason]:
        q = select(InconclusiveReason)
        if active_only:
            q = q.where(InconclusiveReason.is_active.is_(True))
        r = await self._s.execute(q)
        return list(r.scalars().all())

    async def get_inconclusive_reason(self, code: str) -> Optional[InconclusiveReason]:
        r = await self._s.execute(select(InconclusiveReason).where(InconclusiveReason.code == code))
        return r.scalar_one_or_none()

    async def insert_inconclusive_reason_if_absent(self, data: dict) -> InconclusiveReason:
        existing = await self.get_inconclusive_reason(data["code"])
        if existing is not None:
            return existing
        obj = InconclusiveReason(**data)
        self._s.add(obj)
        await self._s.flush()
        return obj

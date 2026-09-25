import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.testcases.models import TestCase, TestCaseCriterion


class TestCaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(
        self,
        certification_id: uuid.UUID,
        code: str,
        name: str,
        preconditions: list,
        steps: list,
        expected_result: str,
        boundary: Optional[str] = None,
        order: int = 0,
    ) -> TestCase:
        tc = TestCase(
            certification_id=certification_id,
            code=code,
            name=name,
            preconditions=preconditions,
            steps=steps,
            expected_result=expected_result,
            boundary=boundary,
            order=order,
        )
        self._s.add(tc)
        await self._s.flush()
        return tc

    async def link_criteria(self, test_case_id: uuid.UUID, criterion_ids: list[uuid.UUID]) -> None:
        # Eliminar links anteriores
        q = select(TestCaseCriterion).where(TestCaseCriterion.test_case_id == test_case_id)
        result = await self._s.execute(q)
        for link in result.scalars().all():
            await self._s.delete(link)
        # Crear nuevos
        for cid in criterion_ids:
            self._s.add(TestCaseCriterion(test_case_id=test_case_id, criterion_id=cid))

    async def commit_and_refresh(self, tc: TestCase) -> TestCase:
        await self._s.commit()
        await self._s.refresh(tc)
        return tc

    async def get(self, test_case_id: uuid.UUID) -> Optional[TestCase]:
        q = select(TestCase).where(TestCase.id == test_case_id)
        result = await self._s.execute(q)
        return result.scalar_one_or_none()

    async def list_by_cert(self, certification_id: uuid.UUID) -> list[TestCase]:
        q = select(TestCase).where(
            TestCase.certification_id == certification_id
        ).order_by(TestCase.order, TestCase.code)
        result = await self._s.execute(q)
        return list(result.scalars().all())

    async def update(self, tc: TestCase, **kwargs: object) -> TestCase:
        for k, v in kwargs.items():
            if v is not None:
                setattr(tc, k, v)
        await self._s.commit()
        await self._s.refresh(tc)
        return tc

    async def delete(self, tc: TestCase) -> None:
        await self._s.delete(tc)
        await self._s.commit()

    async def next_code(self, certification_id: uuid.UUID) -> str:
        cases = await self.list_by_cert(certification_id)
        return f"CP-{len(cases) + 1:02d}"

    async def get_criterion_links(self, test_case_id: uuid.UUID) -> list[uuid.UUID]:
        q = select(TestCaseCriterion.criterion_id).where(
            TestCaseCriterion.test_case_id == test_case_id
        )
        result = await self._s.execute(q)
        return list(result.scalars().all())

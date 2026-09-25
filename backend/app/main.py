from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging
from app.certifications.router import router as certifications_router
from app.context.router import router as context_router
from app.testcases.router import router as testcases_router
from app.testdata.router import router as testdata_router
from app.users.router import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(settings.APP_ENV)
    log = structlog.get_logger()
    log.info("startup", env=settings.APP_ENV)
    yield
    log.info("shutdown")


app = FastAPI(
    title="Copiloto de Certificación QA",
    version="0.1.0",
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url=None,
    lifespan=lifespan,
)


app.include_router(users_router)
app.include_router(certifications_router)
app.include_router(context_router)
app.include_router(testcases_router)
app.include_router(testdata_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

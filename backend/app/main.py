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
from app.evidence.router import router as evidence_router
from app.deliverables.router import router as deliverables_router
from app.metrics.router import router as metrics_router
from app.users.router import router as users_router, admin_router
from app.core.tasks_router import router as tasks_router
from app.knowledge.router import router as knowledge_router
from app.core.neo4j_client import close_driver, get_driver


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(settings.APP_ENV)
    log = structlog.get_logger()
    log.info("startup", env=settings.APP_ENV)
    # Warm-up Neo4j connection (non-fatal if unavailable)
    app.state.neo4j = get_driver()
    if app.state.neo4j is not None:
        log.info("neo4j_connected", uri=settings.NEO4J_URI)
    yield
    await close_driver()
    log.info("shutdown")


app = FastAPI(
    title="Copiloto de Certificación QA",
    version="0.1.0",
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url=None,
    lifespan=lifespan,
)


app.include_router(users_router)
app.include_router(admin_router)
app.include_router(certifications_router)
app.include_router(context_router)
app.include_router(testcases_router)
app.include_router(testdata_router)
app.include_router(evidence_router)
app.include_router(deliverables_router)
app.include_router(metrics_router)
app.include_router(tasks_router)
app.include_router(knowledge_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

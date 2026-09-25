"""Cliente Neo4j singleton para el Mapa Vivo (RF-60 a RF-63)."""
from __future__ import annotations

import structlog

from app.core.config import settings

_driver = None
log = structlog.get_logger()


def get_driver():
    """Retorna el driver AsyncGraphDatabase o None si NEO4J_ENABLED=False."""
    global _driver
    if not settings.NEO4J_ENABLED:
        return None
    if _driver is None:
        try:
            from neo4j import AsyncGraphDatabase
            _driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
        except Exception as exc:
            log.warning("neo4j_driver_init_failed", error=str(exc))
            return None
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        try:
            await _driver.close()
        except Exception:
            pass
        _driver = None

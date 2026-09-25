"""Repositorio de acceso al grafo Neo4j (RF-60 a RF-63)."""
from __future__ import annotations

import structlog

from app.knowledge.models import (
    NODE_CASE,
    NODE_CERT,
    NODE_FEATURE,
    NODE_MESSAGE,
    NODE_MODULE,
    NODE_RULE,
    NODE_TERM,
    REL_COVERS,
    REL_HAS_CASE,
    REL_IN_MODULE,
    REL_TRIGGERS,
    REL_VALIDATES,
)

log = structlog.get_logger()


class KnowledgeRepository:
    def __init__(self, driver) -> None:
        self._driver = driver

    # ── RF-60: Ingestar certificación ─────────────────────────────────────────

    async def record_certification(self, cert_data: dict) -> None:
        """Escribe (MERGE) la certificación y sus relaciones en el grafo."""
        if self._driver is None:
            return

        async def _write(tx):
            module = cert_data.get("module", "")
            cert_id = cert_data.get("cert_id", "")
            cert_title = cert_data.get("title", "")
            cert_type = cert_data.get("type", "")
            cases = cert_data.get("cases", [])

            await tx.run(
                f"""
                MERGE (m:{NODE_MODULE} {{name: $module}})
                MERGE (c:{NODE_CERT} {{id: $cert_id}})
                  ON CREATE SET c.title = $title, c.type = $type
                  ON MATCH  SET c.title = $title, c.type = $type
                MERGE (c)-[:{REL_IN_MODULE}]->(m)
                """,
                module=module, cert_id=cert_id, title=cert_title, type=cert_type,
            )

            for case in cases:
                await tx.run(
                    f"""
                    MERGE (tc:{NODE_CASE} {{id: $tc_id}})
                      ON CREATE SET tc.name = $name, tc.result = $result
                      ON MATCH  SET tc.name = $name, tc.result = $result
                    WITH tc
                    MATCH (cert:{NODE_CERT} {{id: $cert_id}})
                    MERGE (cert)-[:{REL_HAS_CASE}]->(tc)
                    """,
                    tc_id=case["id"], name=case["name"],
                    result=case.get("result", ""), cert_id=cert_id,
                )

                for feature in case.get("features", []):
                    await tx.run(
                        f"""
                        MERGE (f:{NODE_FEATURE} {{name: $fname}})
                        WITH f
                        MATCH (m:{NODE_MODULE} {{name: $module}})
                        MERGE (f)-[:{REL_IN_MODULE}]->(m)
                        WITH f
                        MATCH (tc:{NODE_CASE} {{id: $tc_id}})
                        MERGE (tc)-[:{REL_COVERS}]->(f)
                        """,
                        fname=feature, module=module, tc_id=case["id"],
                    )

                for rule in case.get("rules", []):
                    await tx.run(
                        f"""
                        MERGE (r:{NODE_RULE} {{text: $rtext}})
                        WITH r
                        MATCH (tc:{NODE_CASE} {{id: $tc_id}})
                        MERGE (tc)-[:{REL_VALIDATES}]->(r)
                        """,
                        rtext=rule, tc_id=case["id"],
                    )

                for msg in case.get("error_messages", []):
                    await tx.run(
                        f"""
                        MERGE (em:{NODE_MESSAGE} {{text: $mtext}})
                        WITH em
                        MATCH (tc:{NODE_CASE} {{id: $tc_id}})
                        MERGE (tc)-[:{REL_TRIGGERS}]->(em)
                        """,
                        mtext=msg, tc_id=case["id"],
                    )

        try:
            async with self._driver.session() as session:
                await session.execute_write(_write)
        except Exception as exc:
            log.warning("neo4j_write_failed", error=str(exc))

    # ── RF-61: Consulta Cypher ────────────────────────────────────────────────

    async def query_graph(self, cypher: str, params: dict | None = None) -> list[dict]:
        if self._driver is None:
            return []
        try:
            async with self._driver.session() as session:
                result = await session.run(cypher, parameters=params or {})
                records = await result.data()
                return [dict(r) for r in records]
        except Exception as exc:
            log.warning("neo4j_query_failed", error=str(exc))
            return []

    # ── RF-62: Sugerencias de regresión ───────────────────────────────────────

    async def suggest_regression(self, module: str, keywords: list[str]) -> list[dict]:
        if self._driver is None:
            return []
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    f"""
                    MATCH (m:{NODE_MODULE} {{name: $module}})<-[:{REL_IN_MODULE}]-(cert:{NODE_CERT})
                    MATCH (cert)-[:{REL_HAS_CASE}]->(tc:{NODE_CASE})
                    RETURN cert.id AS cert_id, cert.title AS cert_title,
                           tc.id AS tc_id, tc.name AS tc_name, tc.result AS tc_result
                    LIMIT 30
                    """,
                    module=module,
                )
                records = await result.data()
                return [dict(r) for r in records]
        except Exception as exc:
            log.warning("neo4j_regression_failed", error=str(exc))
            return []

    # ── RF-63: Glosario ───────────────────────────────────────────────────────

    async def upsert_term(self, name: str, definition: str, synonyms: list[str]) -> None:
        if self._driver is None:
            return

        async def _write(tx):
            await tx.run(
                f"""
                MERGE (t:{NODE_TERM} {{name: $name}})
                  ON CREATE SET t.definition = $definition
                  ON MATCH  SET t.definition = $definition
                SET t.synonyms = $synonyms
                """,
                name=name, definition=definition, synonyms=synonyms,
            )

        try:
            async with self._driver.session() as session:
                await session.execute_write(_write)
        except Exception as exc:
            log.warning("neo4j_term_upsert_failed", error=str(exc))

    async def list_terms(self) -> list[dict]:
        if self._driver is None:
            return []
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    f"MATCH (t:{NODE_TERM}) RETURN t.name AS name, t.definition AS definition, t.synonyms AS synonyms ORDER BY t.name"
                )
                records = await result.data()
                return [
                    {
                        "name": r["name"],
                        "definition": r["definition"] or "",
                        "synonyms": list(r["synonyms"] or []),
                    }
                    for r in records
                ]
        except Exception as exc:
            log.warning("neo4j_list_terms_failed", error=str(exc))
            return []

    async def get_term(self, name: str) -> dict | None:
        if self._driver is None:
            return None
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    f"MATCH (t:{NODE_TERM} {{name: $name}}) RETURN t.name AS name, t.definition AS definition, t.synonyms AS synonyms",
                    name=name,
                )
                records = await result.data()
                if not records:
                    return None
                r = records[0]
                return {"name": r["name"], "definition": r["definition"] or "", "synonyms": list(r["synonyms"] or [])}
        except Exception as exc:
            log.warning("neo4j_get_term_failed", error=str(exc))
            return None

    async def delete_term(self, name: str) -> None:
        if self._driver is None:
            return

        async def _write(tx):
            await tx.run(
                f"MATCH (t:{NODE_TERM} {{name: $name}}) DETACH DELETE t",
                name=name,
            )

        try:
            async with self._driver.session() as session:
                await session.execute_write(_write)
        except Exception as exc:
            log.warning("neo4j_delete_term_failed", error=str(exc))

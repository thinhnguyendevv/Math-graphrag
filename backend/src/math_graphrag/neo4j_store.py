from __future__ import annotations

import os
import json
from typing import Any
import re

from neo4j import GraphDatabase

from .schema import CommunityRecord, GraphExtraction, MathChunk


def normalize_entity_name(name: str) -> str:
    return " ".join(str(name or "").strip().lower().split())


class Neo4jGraphStore:
    def __init__(self, config: dict):
        self.config = config
        neo_cfg = config.get("neo4j", {})
        uri = os.getenv(neo_cfg.get("uri_env", "NEO4J_URI"), "bolt://localhost:7687")
        user = os.getenv(neo_cfg.get("user_env", "NEO4J_USER"), "neo4j")
        password = os.getenv(neo_cfg.get("password_env", "NEO4J_PASSWORD"), "please_change_me")
        self.database = neo_cfg.get("database", "neo4j")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            return [r.data() for r in session.run(cypher, params or {})]

    def reset(self):
        self.query("MATCH (n) DETACH DELETE n")

    def setup_schema(self):
        stmts = [
            "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE e.key IS UNIQUE",
            "CREATE CONSTRAINT community_id IF NOT EXISTS FOR (c:Community) REQUIRE c.id IS UNIQUE",
        ]
        for s in stmts:
            self.query(s)
        fulltext = self.config.get("neo4j", {}).get("fulltext_index", "chunk_fulltext_index")
        self.query(f"CREATE FULLTEXT INDEX {fulltext} IF NOT EXISTS FOR (c:Chunk) ON EACH [c.text, c.heading_path]")
        ent_fulltext = self.config.get("neo4j", {}).get("entity_fulltext_index", "entity_fulltext_index")
        self.query(f"CREATE FULLTEXT INDEX {ent_fulltext} IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.type, e.description, e.semantic_summary, e.definition]")

    def upsert_chunks(self, chunks: list[MathChunk]):
        rows = [c.to_dict() for c in chunks]
        self.query(
            """
            UNWIND $rows AS row
            MERGE (c:Chunk {id: row.id})
            SET c.text = row.text,
                c.book_name = row.book_name,
                c.heading_path = row.heading_path,
                c.page_start = row.page_start,
                c.page_end = row.page_end,
                c.order = row.order,
                c.chunk_strategy = row.metadata.chunk_strategy,
                c.block_kinds = row.metadata.block_kinds,
                c.char_len = row.metadata.char_len
            """,
            {"rows": rows},
        )

    def upsert_extractions(self, extractions: list[GraphExtraction]):
        rows = []
        for x in extractions:
            d = x.to_dict()
            for ent in d.get("entities", []):
                ent["properties_json"] = json.dumps(ent.get("properties") or {}, ensure_ascii=False)
            rows.append(d)
        self.query(
            """
            UNWIND $rows AS ex
            MATCH (c:Chunk {id: ex.chunk_id})
            WITH c, ex
            UNWIND ex.entities AS ent
            WITH c, ent, toLower(trim(ent.name)) AS key
            WHERE key <> ''
            MERGE (e:Entity {key: key})
            ON CREATE SET e.name = ent.name,
                          e.type = ent.type,
                          e.description = ent.description,
                          e.semantic_summary = ent.semantic_summary,
                          e.definition = ent.definition,
                          e.aliases = ent.aliases,
                          e.properties_json = ent.properties_json
            ON MATCH SET e.type = CASE WHEN e.type IS NULL OR e.type = '' OR e.type = 'Concept' THEN ent.type ELSE e.type END,
                         e.description = CASE WHEN e.description IS NULL OR e.description = '' THEN ent.description ELSE e.description END,
                         e.semantic_summary = CASE WHEN e.semantic_summary IS NULL OR e.semantic_summary = '' THEN ent.semantic_summary ELSE e.semantic_summary END,
                         e.definition = CASE WHEN e.definition IS NULL OR e.definition = '' THEN ent.definition ELSE e.definition END,
                         e.aliases = CASE WHEN e.aliases IS NULL THEN ent.aliases ELSE e.aliases END,
                         e.properties_json = CASE WHEN e.properties_json IS NULL OR e.properties_json = '{}' THEN ent.properties_json ELSE e.properties_json END
            MERGE (c)-[:MENTIONS]->(e)
            """,
            {"rows": rows},
        )
        self.query(
            """
            UNWIND $rows AS ex
            UNWIND ex.relationships AS rel
            WITH ex, rel
            WHERE rel.source IS NOT NULL AND rel.target IS NOT NULL
            WITH ex, rel, toLower(trim(rel.source)) AS s_key, toLower(trim(rel.target)) AS t_key
            WHERE s_key <> '' AND t_key <> '' AND s_key <> t_key
            MERGE (s:Entity {key: s_key})
            ON CREATE SET s.name = rel.source, s.type = 'Concept', s.semantic_summary = 'Node được tạo từ relationship khi chưa xuất hiện trong entity list.'
            MERGE (t:Entity {key: t_key})
            ON CREATE SET t.name = rel.target, t.type = 'Concept', t.semantic_summary = 'Node được tạo từ relationship khi chưa xuất hiện trong entity list.'
            MERGE (s)-[r:RELATED {type: rel.type}]->(t)
            SET r.description = rel.description,
                r.semantic = rel.semantic,
                r.evidence = rel.evidence,
                r.weight = rel.weight,
                r.source_chunk_ids = CASE WHEN rel.source_chunk_ids IS NULL OR size(rel.source_chunk_ids)=0 THEN [ex.chunk_id] ELSE rel.source_chunk_ids END
            """,
            {"rows": rows},
        )

    def fetch_entity_edges(self) -> list[tuple[str, str]]:
        rows = self.query("MATCH (a:Entity)-[:RELATED]->(b:Entity) RETURN a.key AS source, b.key AS target")
        return [(r["source"], r["target"]) for r in rows]

    def fetch_relationship_details(self, entity_keys: list[str] | None = None, limit: int = 200) -> list[dict[str, Any]]:
        keys = [normalize_entity_name(k) for k in (entity_keys or []) if normalize_entity_name(k)]
        if keys:
            return self.query(
                """
                MATCH (a:Entity)-[r:RELATED]->(b:Entity)
                WHERE a.key IN $keys AND b.key IN $keys
                RETURN a.key AS source, a.name AS source_name,
                       b.key AS target, b.name AS target_name,
                       r.type AS type, r.description AS description,
                       r.semantic AS semantic, r.weight AS weight,
                       r.evidence AS evidence
                ORDER BY coalesce(r.weight, 1.0) DESC
                LIMIT $limit
                """,
                {"keys": keys, "limit": int(limit)},
            )
        return self.query(
            """
            MATCH (a:Entity)-[r:RELATED]->(b:Entity)
            RETURN a.key AS source, a.name AS source_name,
                   b.key AS target, b.name AS target_name,
                   r.type AS type, r.description AS description,
                   r.semantic AS semantic, r.weight AS weight,
                   r.evidence AS evidence
            ORDER BY coalesce(r.weight, 1.0) DESC
            LIMIT $limit
            """,
            {"limit": int(limit)},
        )

    def fetch_entities(self) -> list[dict[str, Any]]:
        return self.query(
            """
            MATCH (e:Entity)
            RETURN e.key AS key, e.name AS name, e.type AS type,
                   e.description AS description, e.semantic_summary AS semantic_summary,
                   e.definition AS definition, e.aliases AS aliases, e.properties_json AS properties_json
            """
        )

    def upsert_communities(self, communities: list[CommunityRecord]):
        rows = [c.to_dict() for c in communities]
        self.query(
            """
            UNWIND $rows AS row
            MERGE (c:Community {id: row.id})
            SET c.level = row.level,
                c.title = row.title,
                c.summary = row.summary,
                c.entity_names = row.entity_names,
                c.parent_id = row.parent_id,
                c.child_ids = row.child_ids,
                c.relationship_summaries = row.relationship_summaries
            WITH c, row
            UNWIND row.entity_names AS entity_name
            MATCH (e:Entity {key: toLower(trim(entity_name))})
            MERGE (e)-[:IN_COMMUNITY]->(c)
            """,
            {"rows": rows},
        )
        self.query(
            """
            UNWIND $rows AS row
            WITH row WHERE row.parent_id IS NOT NULL AND row.parent_id <> ''
            MATCH (child:Community {id: row.id})
            MATCH (parent:Community {id: row.parent_id})
            MERGE (child)-[:PART_OF]->(parent)
            """,
            {"rows": rows},
        )

    def set_chunk_embeddings(self, rows: list[dict[str, Any]]):
        self.query("""
            UNWIND $rows AS row
            MATCH (c:Chunk {id: row.id})
            SET c.embedding = row.embedding
            """, {"rows": rows})

    def set_entity_embeddings(self, rows: list[dict[str, Any]]):
        self.query("""
            UNWIND $rows AS row
            MATCH (e:Entity {key: row.key})
            SET e.embedding = row.embedding
            """, {"rows": rows})

    def set_community_embeddings(self, rows: list[dict[str, Any]]):
        self.query("""
            UNWIND $rows AS row
            MATCH (c:Community {id: row.id})
            SET c.embedding = row.embedding
            """, {"rows": rows})

    def create_vector_indexes(self, dim: int):
        neo_cfg = self.config.get("neo4j", {})
        indexes = [
            (neo_cfg.get("chunk_vector_index", "chunk_embedding_index"), "Chunk"),
            (neo_cfg.get("entity_vector_index", "entity_embedding_index"), "Entity"),
            (neo_cfg.get("community_vector_index", "community_embedding_index"), "Community"),
        ]
        for index_name, label in indexes:
            self.query(
                f"""
                CREATE VECTOR INDEX {index_name} IF NOT EXISTS
                FOR (n:{label}) ON (n.embedding)
                OPTIONS {{indexConfig: {{`vector.dimensions`: $dim, `vector.similarity_function`: 'cosine'}}}}
                """,
                {"dim": dim},
            )

    def vector_search(self, label: str, index_name: str, embedding: list[float], top_k: int) -> list[dict[str, Any]]:
        return self.query(
            f"""
            CALL db.index.vector.queryNodes($index, $top_k, $embedding)
            YIELD node, score
            RETURN labels(node)[0] AS label, node {{.*}} AS node, score
            ORDER BY score DESC
            """,
            {"index": index_name, "top_k": top_k, "embedding": embedding},
        )

    @staticmethod
    def _safe_fulltext_query(question: str) -> str:
        tokens = re.findall(r"[A-Za-zÀ-ỹ0-9_\-]{2,}", question or "", flags=re.UNICODE)
        tokens = [t for t in tokens if t.strip()]
        if not tokens:
            return (question or "").replace("'", " ").strip() or "*"
        return " OR ".join(tokens[:16])

    def fulltext_search_chunks(self, question: str, top_k: int) -> list[dict[str, Any]]:
        index = self.config.get("neo4j", {}).get("fulltext_index", "chunk_fulltext_index")
        safe_q = self._safe_fulltext_query(question)
        return self.query(
            f"""
            CALL db.index.fulltext.queryNodes($index, $q) YIELD node, score
            RETURN node {{.*}} AS node, score
            ORDER BY score DESC LIMIT $top_k
            """,
            {"index": index, "q": safe_q, "top_k": top_k},
        )

    def fulltext_search_entities(self, question: str, top_k: int) -> list[dict[str, Any]]:
        index = self.config.get("neo4j", {}).get("entity_fulltext_index", "entity_fulltext_index")
        safe_q = self._safe_fulltext_query(question)
        return self.query(
            f"""
            CALL db.index.fulltext.queryNodes($index, $q) YIELD node, score
            RETURN node {{.*}} AS node, score
            ORDER BY score DESC LIMIT $top_k
            """,
            {"index": index, "q": safe_q, "top_k": top_k},
        )

    def chunks_mentioning_entities(self, entity_keys: list[str], limit: int = 8) -> list[dict[str, Any]]:
        keys = []
        seen = set()
        for key in entity_keys:
            k = normalize_entity_name(key)
            if k and k not in seen:
                seen.add(k)
                keys.append(k)
        if not keys:
            return []
        return self.query(
            """
            MATCH (c:Chunk)-[:MENTIONS]->(e:Entity)
            WHERE e.key IN $keys
            WITH c, count(DISTINCT e) AS hits
            RETURN c {.*} AS node, toFloat(hits) AS score
            ORDER BY hits DESC, c.order ASC
            LIMIT $limit
            """,
            {"keys": keys, "limit": int(limit)},
        )

    def expand_from_entities(self, entity_keys: list[str], depth: int, limit: int) -> list[dict[str, Any]]:
        keys = [normalize_entity_name(k) for k in entity_keys if normalize_entity_name(k)]
        if not keys:
            return []
        return self.query(
            f"""
            MATCH (e:Entity)
            WHERE e.key IN $keys
            MATCH p=(e)-[:RELATED*1..{int(depth)}]-(n:Entity)
            RETURN [x IN nodes(p) | coalesce(x.name, x.key)] AS path,
                   [r IN relationships(p) | coalesce(r.type, type(r))] AS relations
            LIMIT $limit
            """,
            {"keys": keys, "limit": int(limit)},
        )

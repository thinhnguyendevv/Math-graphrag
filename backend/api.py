from __future__ import annotations

import os
import traceback
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from math_graphrag.config import load_config
from math_graphrag.embedding import get_embedding_model
from math_graphrag.llm import LLMQuotaError, get_llm
from math_graphrag.neo4j_store import Neo4jGraphStore
from math_graphrag.retrieval import GraphRAGRetriever

load_dotenv()

app = FastAPI(title="Math GraphRAG API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str
    mode: str | None = "graphrag"
    top_k: int | None = None


class BuildRequest(BaseModel):
    text: str
    filename: str | None = None


@lru_cache(maxsize=1)
def get_retriever() -> GraphRAGRetriever:
    config_path = Path(os.getenv("MATH_GRAPHRAG_CONFIG", "configs/config.yaml"))
    config = load_config(config_path)
    llm = get_llm(config)
    embedding_model = get_embedding_model(config)
    store = Neo4jGraphStore(config)
    return GraphRAGRetriever(config=config, store=store, llm=llm, embedding_model=embedding_model)


def get_store() -> Neo4jGraphStore:
    return get_retriever().store


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        store = get_store()
        rows = store.query("RETURN 1 AS ok")
        return {"ok": True, "neo4j": rows[0].get("ok") == 1 if rows else False}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@app.get("/api/graph/stats")
def graph_stats() -> dict[str, int]:
    try:
        store = get_store()
        rows = store.query(
            """
            MATCH (n)
            RETURN
              count { (n:Chunk) } AS total_chunks,
              count { (n:Entity) } AS total_entities,
              count { (n:Community) } AS total_communities,
              count { (:Entity)-[:RELATED]->(:Entity) } AS total_relationships
            """
        )
        row = rows[0] if rows else {}
        return {
            "total_chunks": int(row.get("total_chunks") or 0),
            "total_entities": int(row.get("total_entities") or 0),
            "total_communities": int(row.get("total_communities") or 0),
            "total_relationships": int(row.get("total_relationships") or 0),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không đọc được thống kê Neo4j: {exc}")


@app.get("/api/graph/data")
def graph_data(limit: int = 120) -> dict[str, Any]:
    try:
        store = get_store()
        nodes_rows = store.query(
            """
            MATCH (e:Entity)
            RETURN coalesce(e.key, toLower(e.name)) AS id,
                   coalesce(e.name, e.key) AS label,
                   coalesce(e.type, 'Concept') AS type,
                   coalesce(e.semantic_summary, e.description, e.definition, '') AS description
            ORDER BY label
            LIMIT $limit
            """,
            {"limit": int(limit)},
        )
        links_rows = store.query(
            """
            MATCH (a:Entity)-[r:RELATED]->(b:Entity)
            RETURN coalesce(a.name, a.key) AS source,
                   coalesce(b.name, b.key) AS target,
                   coalesce(r.type, type(r)) AS relationship,
                   coalesce(r.semantic, r.description, r.evidence, '') AS description
            LIMIT $limit
            """,
            {"limit": int(limit * 2)},
        )
        communities_rows = store.query(
            """
            MATCH (c:Community)
            RETURN c.id AS id,
                   coalesce(c.title, c.id) AS name,
                   coalesce(c.summary, '') AS description,
                   coalesce(c.entity_names, []) AS members
            LIMIT $limit
            """,
            {"limit": int(limit)},
        )
        return {
            "nodes": nodes_rows,
            "links": links_rows,
            "communities": communities_rows,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không đọc được graph từ Neo4j: {exc}")


@app.post("/api/query")
def query_graph(req: QueryRequest) -> dict[str, Any]:
    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Nội dung câu hỏi không được để trống")
    try:
        retriever = get_retriever()
        if req.top_k and req.top_k > 0:
            retriever.config.setdefault("retrieval", {})["final_context_chunks"] = int(req.top_k)
        result = retriever.answer(question)
        return {
            "answer": result.get("answer") or "Không có câu trả lời.",
            "mode": req.mode or "graphrag",
            "sources": result.get("sources", []),
            "graph_paths": result.get("graph_paths", []),
            "query_understanding": result.get("query_understanding", {}),
        }
    except LLMQuotaError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except Exception as exc:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Lỗi truy vấn GraphRAG: {exc}")


@app.post("/api/graph/reset")
def reset_graph() -> dict[str, Any]:
    try:
        get_store().reset()
        return {"success": True, "message": "Đã xóa dữ liệu Neo4j"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không reset được Neo4j: {exc}")


@app.post("/api/graph/build")
def build_graph(_: BuildRequest) -> dict[str, Any]:
    raise HTTPException(
        status_code=501,
        detail="Frontend đã nối với backend GraphRAG thật. Để nạp sách mới, hãy chạy scripts/run_pipeline.py hoặc scripts/02_build_index.py trong backend rồi refresh frontend.",
    )

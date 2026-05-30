from __future__ import annotations

from pathlib import Path

from tqdm import tqdm

from .chunking import chunk_markdown_file
from .community import detect_communities
from .embedding import get_embedding_model
from .extraction import extract_graph_for_chunks
from .llm import get_llm
from .neo4j_store import Neo4jGraphStore
from .utils import ensure_dir, save_jsonl


def load_all_chunks(config: dict):
    clean_dir = Path(config.get("paths", {}).get("clean_md_dir", "data/md_clean"))
    book_name = config.get("project", {}).get("book_name")
    chunks = []
    for md in sorted(clean_dir.glob("*.md")):
        chunks.extend(chunk_markdown_file(md, config, book_name=book_name or md.stem))
    return chunks


def build_index(config: dict, logger=None):
    llm = get_llm(config)
    embedder = get_embedding_model(config)
    store = Neo4jGraphStore(config)

    if config.get("neo4j", {}).get("reset_before_index", False):
        if logger:
            logger.info("Reset Neo4j database")
        store.reset()

    store.setup_schema()

    chunks = load_all_chunks(config)
    if not chunks:
        raise RuntimeError("Không tìm thấy file .md trong data/md_clean. Hãy chạy preprocess hoặc đặt file md vào đúng thư mục.")

    if logger:
        logger.info("Loaded %d chunks", len(chunks))

    out_dir = ensure_dir(config.get("paths", {}).get("output_dir", "data/output"))
    save_jsonl(out_dir / "chunks.jsonl", [c.to_dict() for c in chunks])

    store.upsert_chunks(chunks)

    extractions = extract_graph_for_chunks(chunks, llm, config)
    store.upsert_extractions(extractions)

    communities = detect_communities(store, llm, config)
    store.upsert_communities(communities)
    save_jsonl(out_dir / "communities.jsonl", [c.to_dict() for c in communities])

    # Embedding dimension is needed before creating vector indexes.
    probe = embedder.embed_query("kiểm tra kích thước vector")
    store.create_vector_indexes(len(probe))

    chunk_texts = [f"{c.heading_path}\n{c.text}" for c in chunks]
    chunk_embs = embedder.embed_documents(chunk_texts)
    store.set_chunk_embeddings([{"id": c.id, "embedding": e} for c, e in zip(chunks, chunk_embs)])

    entities = store.fetch_entities()
    entity_texts = [f"{e.get('name','')}\n{e.get('type','')}\n{e.get('description','')}\n{e.get('semantic_summary','')}\n{e.get('definition','')}" for e in entities]
    if entity_texts:
        entity_embs = embedder.embed_documents(entity_texts)
        store.set_entity_embeddings([{"key": e["key"], "embedding": emb} for e, emb in zip(entities, entity_embs)])

    comm_texts = [f"level={c.level}\n{c.title}\n{c.summary}\nQuan hệ: {'; '.join(c.relationship_summaries[:8])}" for c in communities]
    if comm_texts:
        comm_embs = embedder.embed_documents(comm_texts)
        store.set_community_embeddings([{"id": c.id, "embedding": emb} for c, emb in zip(communities, comm_embs)])

    return {
        "chunks": len(chunks),
        "communities": len(communities),
        "entities": len(entities),
    }

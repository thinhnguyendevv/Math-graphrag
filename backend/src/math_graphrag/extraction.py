from __future__ import annotations

import json
import re
from typing import Any

from tqdm import tqdm

from .prompts import GRAPH_EXTRACTION_SYSTEM, GRAPH_EXTRACTION_USER, BATCH_GRAPH_EXTRACTION_USER
from .schema import Entity, GraphExtraction, MathChunk, Relationship
from .utils import append_jsonl, ensure_dir


ALLOWED_ENTITY_TYPES = {
    "CONCEPT": "Concept",
    "FORMULA": "Formula",
    "THEOREM": "Theorem",
    "METHOD": "Method",
    "PROBLEMTYPE": "ProblemType",
    "PROBLEM_TYPE": "ProblemType",
    "CONDITION": "Condition",
    "PROPERTY": "Property",
    "EXAMPLE": "Example",
    "SECTION": "Section",
}


def _extract_json(text: str) -> dict[str, Any]:
    text = str(text or "").strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"Không tìm thấy JSON trong LLM output: {text[:500]}")
    return json.loads(m.group(0))


def _normalize_extraction_keys(data: dict[str, Any]) -> dict[str, Any]:
    if "entities" not in data and "nodes" in data:
        data["entities"] = data.get("nodes", [])
    if "relationships" not in data and "edges" in data:
        data["relationships"] = data.get("edges", [])
    return data


def _clean_entity_type(value: str) -> str:
    raw = str(value or "Concept").strip().replace(" ", "_").replace("-", "_")
    return ALLOWED_ENTITY_TYPES.get(raw.upper(), raw[:40] or "Concept")


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, tuple):
        return [str(x).strip() for x in value if str(x).strip()]
    s = str(value).strip()
    return [s] if s else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def parse_extraction(chunk_id: str, data: dict[str, Any]) -> GraphExtraction:
    data = _normalize_extraction_keys(data)

    entities: list[Entity] = []
    seen_entities: set[str] = set()
    for e in data.get("entities", []) or []:
        if not isinstance(e, dict):
            continue
        name = str(e.get("name", "")).strip()
        if not name or len(name) > 120:
            continue
        key = " ".join(name.lower().split())
        if key in seen_entities:
            continue
        seen_entities.add(key)
        description = str(e.get("description", "")).strip()
        semantic_summary = str(e.get("semantic_summary") or e.get("semantic") or description).strip()
        entities.append(
            Entity(
                name=name,
                type=_clean_entity_type(e.get("type", "Concept")),
                description=description,
                semantic_summary=semantic_summary,
                definition=str(e.get("definition", "")).strip(),
                aliases=_as_str_list(e.get("aliases")),
                properties=_as_dict(e.get("properties")),
            )
        )

    relationships: list[Relationship] = []
    seen_rels: set[tuple[str, str, str]] = set()
    for r in data.get("relationships", []) or []:
        if not isinstance(r, dict):
            continue
        source = str(r.get("source", "")).strip()
        target = str(r.get("target", "")).strip()
        if not source or not target or source.lower() == target.lower():
            continue
        rel_type = str(r.get("type", "RELATED_TO")).strip().upper().replace(" ", "_").replace("-", "_") or "RELATED_TO"
        rel_key = (source.lower(), target.lower(), rel_type)
        if rel_key in seen_rels:
            continue
        seen_rels.add(rel_key)
        source_chunk_ids = _as_str_list(r.get("source_chunk_ids")) or [chunk_id]
        relationships.append(
            Relationship(
                source=source,
                target=target,
                type=rel_type,
                description=str(r.get("description", "")).strip(),
                semantic=str(r.get("semantic") or r.get("meaning") or "").strip(),
                evidence=str(r.get("evidence", "")).strip(),
                weight=float(r.get("weight", 1.0) or 1.0),
                source_chunk_ids=source_chunk_ids,
            )
        )

    return GraphExtraction(chunk_id=chunk_id, entities=entities, relationships=relationships)


MATH_TERMS = [
    ("Đạo hàm", "Concept"), ("Hàm số", "Concept"), ("Tiếp tuyến", "Concept"),
    ("Giới hạn", "Concept"), ("Cực trị", "Concept"), ("Cực đại", "Concept"),
    ("Cực tiểu", "Concept"), ("Đồng biến", "Property"), ("Nghịch biến", "Property"),
    ("Tính đơn điệu", "Property"), ("Bảng biến thiên", "Method"),
    ("Khảo sát hàm số", "Method"), ("Đồ thị hàm số", "Concept"),
    ("Tiệm cận", "Concept"), ("Tiệm cận đứng", "Concept"), ("Tiệm cận ngang", "Concept"),
    ("Tiệm cận xiên", "Concept"), ("Nguyên hàm", "Concept"), ("Tích phân", "Concept"),
    ("Số phức", "Concept"), ("Logarit", "Concept"), ("Hàm số mũ", "Concept"),
    ("Hàm số logarit", "Concept"), ("Phương trình", "ProblemType"), ("Bất phương trình", "ProblemType"),
]


def rule_based_fallback_extract(chunk: MathChunk) -> GraphExtraction:
    text_lower = chunk.text.lower()
    found: list[Entity] = []
    for term, term_type in MATH_TERMS:
        if term.lower() in text_lower:
            found.append(
                Entity(
                    name=term,
                    type=term_type,
                    description=f"Thuật ngữ xuất hiện trong mục: {chunk.heading_path}",
                    semantic_summary=f"Node được phát hiện bằng luật vì thuật ngữ '{term}' xuất hiện trong chunk.",
                    aliases=[],
                    properties={"heading_path": chunk.heading_path, "page_start": chunk.page_start, "page_end": chunk.page_end},
                )
            )
    heading_parts = [x.strip() for x in str(chunk.heading_path or "").split(">") if x.strip()]
    for h in heading_parts[-2:]:
        if 3 <= len(h) <= 80:
            found.append(
                Entity(
                    name=h,
                    type="Section",
                    description=f"Mục trong sách: {chunk.heading_path}",
                    semantic_summary="Node đại diện cho heading/mục sách để nối nội dung chunk với cấu trúc tài liệu.",
                    aliases=[],
                    properties={"book_name": chunk.book_name},
                )
            )
    seen = set()
    unique_entities: list[Entity] = []
    for e in found:
        if e.normalized_name not in seen:
            seen.add(e.normalized_name)
            unique_entities.append(e)
    relationships: list[Relationship] = []
    sections = [e for e in unique_entities if e.type == "Section"]
    concepts = [e for e in unique_entities if e.type != "Section"]
    if sections and concepts:
        center = sections[-1].name
        for e in concepts:
            relationships.append(Relationship(
                source=center,
                target=e.name,
                type="MENTIONS_TOPIC",
                description="Mục sách có nhắc tới chủ đề toán học này.",
                semantic="Quan hệ nối cấu trúc tài liệu với khái niệm để hỗ trợ truy hồi theo mục/chương.",
                evidence=chunk.text[:200],
                weight=0.4,
                source_chunk_ids=[chunk.id],
            ))
    elif len(unique_entities) >= 2:
        center = unique_entities[0].name
        for e in unique_entities[1:]:
            relationships.append(Relationship(
                source=center,
                target=e.name,
                type="RELATED_TO",
                description="Hai node cùng xuất hiện trong một chunk.",
                semantic="Đồng xuất hiện trong cùng ngữ cảnh sách.",
                evidence=chunk.text[:200],
                weight=0.3,
                source_chunk_ids=[chunk.id],
            ))
    return GraphExtraction(chunk_id=chunk.id, entities=unique_entities, relationships=relationships)


def _save_extraction_error(config: dict, chunk: MathChunk, raw: str, error: Exception):
    out_dir = ensure_dir(config.get("paths", {}).get("output_dir", "data/output"))
    append_jsonl(out_dir / "debug_extraction_errors.jsonl", {
        "chunk_id": chunk.id,
        "heading_path": chunk.heading_path,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "error": str(error),
        "raw": str(raw)[:3000],
        "text_preview": chunk.text[:1000],
    })


def extract_graph_from_chunk(chunk: MathChunk, llm, config: dict) -> GraphExtraction:
    prompt = GRAPH_EXTRACTION_SYSTEM + "\n\n" + GRAPH_EXTRACTION_USER.format(
        chunk_id=chunk.id,
        book_name=chunk.book_name,
        heading_path=chunk.heading_path,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        text=chunk.text,
    )
    retries = int(config.get("extraction", {}).get("max_retries", 2))
    use_rule_fallback = bool(config.get("extraction", {}).get("rule_fallback", True))
    last_error: Exception | None = None
    last_raw = ""
    for _ in range(retries + 1):
        try:
            last_raw = str(llm.invoke(prompt))
            ge = parse_extraction(chunk.id, _extract_json(last_raw))
            if not ge.entities and use_rule_fallback:
                fallback = rule_based_fallback_extract(chunk)
                if fallback.entities:
                    return fallback
            return ge
        except Exception as e:
            last_error = e
    if last_error is not None:
        _save_extraction_error(config, chunk, last_raw, last_error)
    return rule_based_fallback_extract(chunk) if use_rule_fallback else GraphExtraction(chunk_id=chunk.id)


def _format_batch_chunks(chunks: list[MathChunk]) -> str:
    parts = []
    max_chars = int(12000 / max(1, len(chunks)))
    for c in chunks:
        text = c.text[:max_chars]
        parts.append(
            f"---\nchunk_id: {c.id}\nbook: {c.book_name}\nheading_path: {c.heading_path}\npage_start: {c.page_start}\npage_end: {c.page_end}\ntext:\n{text}"
        )
    return "\n\n".join(parts)


def _dedupe_extraction(ge: GraphExtraction) -> GraphExtraction:
    ent_seen = set()
    ents = []
    for e in ge.entities:
        if e.normalized_name not in ent_seen:
            ent_seen.add(e.normalized_name)
            ents.append(e)
    rel_seen = set()
    rels = []
    for r in ge.relationships:
        key = (r.source.lower(), r.target.lower(), r.type)
        if key not in rel_seen:
            rel_seen.add(key)
            rels.append(r)
    return GraphExtraction(chunk_id=ge.chunk_id, entities=ents, relationships=rels)


def extract_graph_for_batch(chunks: list[MathChunk], llm, config: dict) -> list[GraphExtraction]:
    if len(chunks) <= 1:
        return [extract_graph_from_chunk(chunks[0], llm, config)]
    prompt = GRAPH_EXTRACTION_SYSTEM + "\n\n" + BATCH_GRAPH_EXTRACTION_USER.format(chunks=_format_batch_chunks(chunks))
    retries = int(config.get("extraction", {}).get("max_retries", 2))
    use_rule_fallback = bool(config.get("extraction", {}).get("rule_fallback", True))
    by_id = {c.id: GraphExtraction(chunk_id=c.id) for c in chunks}
    last_raw = ""
    last_error: Exception | None = None
    for _ in range(retries + 1):
        try:
            last_raw = str(llm.invoke(prompt))
            data = _extract_json(last_raw)
            for item in data.get("chunk_extractions", []) or []:
                if not isinstance(item, dict):
                    continue
                cid = str(item.get("chunk_id", "")).strip()
                if cid in by_id:
                    by_id[cid] = parse_extraction(cid, item)
            cross = data.get("cross_chunk_relationships", []) or []
            if cross:
                first_id = chunks[0].id
                holder = by_id[first_id]
                holder.relationships.extend(parse_extraction(first_id, {"entities": [], "relationships": cross}).relationships)
                by_id[first_id] = holder
            outputs = [_dedupe_extraction(by_id[c.id]) for c in chunks]
            if use_rule_fallback:
                for i, ge in enumerate(outputs):
                    if not ge.entities:
                        outputs[i] = rule_based_fallback_extract(chunks[i])
            return outputs
        except Exception as e:
            last_error = e
    if last_error is not None:
        for c in chunks:
            _save_extraction_error(config, c, last_raw, last_error)
    return [rule_based_fallback_extract(c) if use_rule_fallback else GraphExtraction(chunk_id=c.id) for c in chunks]


def extract_graph_for_chunks(chunks: list[MathChunk], llm, config: dict) -> list[GraphExtraction]:
    outputs: list[GraphExtraction] = []
    jsonl_path = config.get("extraction", {}).get("save_jsonl")
    batch_size = max(1, int(config.get("extraction", {}).get("batch_size", 1)))
    total_entities = 0
    total_relationships = 0

    for start in tqdm(range(0, len(chunks), batch_size), desc="Extract graph batches"):
        batch = chunks[start:start + batch_size]
        batch_outputs = extract_graph_for_batch(batch, llm, config) if batch_size > 1 else [extract_graph_from_chunk(batch[0], llm, config)]
        for ge in batch_outputs:
            total_entities += len(ge.entities)
            total_relationships += len(ge.relationships)
            outputs.append(ge)
            if jsonl_path:
                append_jsonl(jsonl_path, ge.to_dict())

    print(f"[EXTRACTION] chunks={len(chunks)} | batch_size={batch_size} | entities={total_entities} | relationships={total_relationships}")
    return outputs

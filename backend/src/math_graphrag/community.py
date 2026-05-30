from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

import networkx as nx

from .schema import CommunityRecord
from .prompts import COMMUNITY_SUMMARY_PROMPT


def _safe_json(text: str) -> dict:
    text = str(text or "").strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        return {"title": "Cụm tri thức", "summary": text[:800]}


def _node_key_set(values) -> frozenset[str]:
    return frozenset(str(v) for v in values if str(v))


def _fallback_hierarchical_communities(g: nx.Graph, max_levels: int, min_size: int, max_cluster_size: int) -> dict[int, list[set[str]]]:
    """Fallback thuần NetworkX: chia đệ quy community lớn để có nhiều level."""
    levels: dict[int, list[set[str]]] = defaultdict(list)
    current = [set(c) for c in nx.connected_components(g)]
    if not current:
        return {}
    for level in range(max_levels):
        next_level: list[set[str]] = []
        for nodes in current:
            if len(nodes) < min_size:
                continue
            levels[level].append(set(nodes))
            if level == max_levels - 1 or len(nodes) <= max_cluster_size:
                continue
            sub = g.subgraph(nodes).copy()
            try:
                parts = [set(c) for c in nx.algorithms.community.greedy_modularity_communities(sub)]
            except Exception:
                parts = []
            # Chỉ đi tiếp nếu thật sự tách được.
            if len(parts) > 1:
                next_level.extend([p for p in parts if len(p) >= min_size])
        current = next_level
        if not current:
            break
    return levels


def _leiden_hierarchical_communities(g: nx.Graph, max_levels: int) -> dict[int, list[set[str]]]:
    from graspologic.partition import hierarchical_leiden
    partitions = hierarchical_leiden(g)
    grouped = defaultdict(lambda: defaultdict(set))
    for p in partitions:
        level = int(getattr(p, "level", 0))
        if level >= max_levels:
            continue
        cluster = str(getattr(p, "cluster", "0"))
        node = str(getattr(p, "node"))
        grouped[level][cluster].add(node)
    return {level: list(clusters.values()) for level, clusters in grouped.items()}


def _assign_parent_child(records: list[CommunityRecord], key_sets: dict[str, frozenset[str]]) -> list[CommunityRecord]:
    # Parent là cụm ở level liền trước chứa toàn bộ node của child và có kích thước nhỏ nhất.
    by_level = defaultdict(list)
    for r in records:
        by_level[r.level].append(r)
    for child in records:
        child_set = key_sets.get(child.id, frozenset())
        candidates = []
        for parent in by_level.get(child.level - 1, []):
            pset = key_sets.get(parent.id, frozenset())
            if child_set and child_set.issubset(pset) and child.id != parent.id:
                candidates.append((len(pset), parent))
        if candidates:
            parent = sorted(candidates, key=lambda x: x[0])[0][1]
            child.parent_id = parent.id
            if child.id not in parent.child_ids:
                parent.child_ids.append(child.id)
    return records


def _relationship_lines(store, keys: list[str], limit: int = 30) -> list[str]:
    rows = store.fetch_relationship_details(keys, limit=limit)
    lines = []
    for r in rows:
        s = r.get("source_name") or r.get("source")
        t = r.get("target_name") or r.get("target")
        typ = r.get("type") or "RELATED_TO"
        desc = r.get("description") or r.get("semantic") or ""
        lines.append(f"- {s} --{typ}--> {t}: {desc}"[:350])
    return lines


def detect_communities(store, llm, config: dict) -> list[CommunityRecord]:
    """
    Phân cụm phân tầng theo tinh thần Microsoft GraphRAG:
    1. Dựng entity graph từ node + relationship.
    2. Chạy hierarchical Leiden nếu có, fallback recursive greedy nếu không.
    3. Tạo community ở từng level, có parent/child, summary từ entity + quan hệ nội bộ.
    """
    edges = store.fetch_entity_edges()
    entities = store.fetch_entities()
    key_to_entity = {e["key"]: e for e in entities}
    key_to_name = {e["key"]: e.get("name") or e["key"] for e in entities}

    g = nx.Graph()
    for e in entities:
        g.add_node(e["key"])
    for edge in edges:
        if len(edge) >= 2:
            a, b = edge[0], edge[1]
            if a and b and a != b:
                g.add_edge(a, b)

    if g.number_of_nodes() == 0:
        return []

    comm_cfg = config.get("community", {})
    max_levels = int(comm_cfg.get("max_levels", 3))
    min_size = int(comm_cfg.get("min_community_size", 3))
    max_cluster_size = int(comm_cfg.get("max_cluster_size", 80))

    try:
        level_groups = _leiden_hierarchical_communities(g, max_levels=max_levels)
    except Exception:
        level_groups = _fallback_hierarchical_communities(g, max_levels=max_levels, min_size=min_size, max_cluster_size=max_cluster_size)

    # Bảo đảm có ít nhất một level nếu thuật toán trả rỗng.
    if not level_groups:
        level_groups = {0: [set(c) for c in nx.algorithms.community.greedy_modularity_communities(g)]}

    records: list[CommunityRecord] = []
    key_sets: dict[str, frozenset[str]] = {}
    seen_sets: set[tuple[int, tuple[str, ...]]] = set()

    for level in sorted(level_groups):
        idx = 0
        for keys in level_groups[level]:
            keys = {str(k) for k in keys if str(k) in key_to_entity}
            if len(keys) < min_size:
                continue
            frozen_tuple = tuple(sorted(keys))
            seen_key = (int(level), frozen_tuple)
            if seen_key in seen_sets:
                continue
            seen_sets.add(seen_key)
            idx += 1
            cid = f"community_L{int(level)}_{idx:05d}"
            key_sets[cid] = _node_key_set(keys)

            entity_lines = []
            for k in sorted(keys)[:120]:
                e = key_to_entity.get(k, {})
                name = e.get("name") or k
                typ = e.get("type") or "Entity"
                sem = e.get("semantic_summary") or e.get("description") or ""
                entity_lines.append(f"- {name} [{typ}]: {sem}"[:300])
            rel_lines = _relationship_lines(store, sorted(keys), limit=40)

            prompt = COMMUNITY_SUMMARY_PROMPT.format(
                level=level,
                entities="\n".join(entity_lines),
                relationships="\n".join(rel_lines) if rel_lines else "- Không có quan hệ nội bộ rõ ràng.",
            )
            try:
                data = _safe_json(llm.invoke(prompt))
            except Exception:
                data = {"title": f"Community L{level}-{idx}", "summary": ", ".join([key_to_name.get(k, k) for k in sorted(keys)[:20]])}
            records.append(
                CommunityRecord(
                    id=cid,
                    level=int(level),
                    title=data.get("title") or f"Community L{level}-{idx}",
                    summary=data.get("summary") or ", ".join([key_to_name.get(k, k) for k in sorted(keys)[:20]]),
                    entity_names=[key_to_name.get(k, k) for k in sorted(keys)],
                    relationship_summaries=rel_lines[:20],
                )
            )

    return _assign_parent_child(records, key_sets)

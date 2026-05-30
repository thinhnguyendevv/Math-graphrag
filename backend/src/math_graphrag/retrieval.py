from __future__ import annotations

from collections import defaultdict
import re

from .prompts import ANSWER_PROMPT
from .query_understanding import QueryUnderstanding, understand_query


class GraphRAGRetriever:
    def __init__(self, config: dict, store, llm, embedding_model):
        self.config = config
        self.store = store
        self.llm = llm
        self.embedding_model = embedding_model

    def _rrf_fuse(self, result_lists: list[list[dict]], k: int = 60) -> list[dict]:
        scores = defaultdict(float)
        items = {}
        for results in result_lists:
            for rank, item in enumerate(results or [], start=1):
                node = item.get("node", {})
                item_id = node.get("id") or node.get("key") or node.get("name")
                if not item_id:
                    continue
                scores[item_id] += 1.0 / (k + rank)
                old = items.get(item_id)
                if old is None or item.get("score", 0) > old.get("score", 0):
                    items[item_id] = item
        fused = []
        for item_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            it = dict(items[item_id])
            it["fused_score"] = score
            fused.append(it)
        return fused

    @staticmethod
    def _filter_chunks_by_page(chunks: list[dict], qu: QueryUnderstanding) -> list[dict]:
        if qu.page_start is None:
            return chunks
        page_end = qu.page_end or qu.page_start
        filtered = []
        for item in chunks:
            node = item.get("node", {})
            c_start = node.get("page_start")
            c_end = node.get("page_end") or c_start
            if c_start is None:
                continue
            if int(c_start) <= page_end and int(c_end) >= qu.page_start:
                filtered.append(item)
        return filtered or chunks

    def _query_texts(self, qu: QueryUnderstanding) -> list[str]:
        # Query decomposition là nguồn chính; variants và keyword/entity là nguồn bổ trợ.
        texts = [
            qu.rewritten_query,
            *qu.sub_queries,
            *qu.query_variants,
            " ".join(qu.entities + qu.keywords),
            qu.original_question,
        ]
        seen = set()
        out = []
        max_queries = int(self.config.get("retrieval", {}).get("max_query_variants", 6))
        for text in texts:
            text = (text or "").strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(text)
            if len(out) >= max_queries:
                break
        return out or [qu.original_question]

    def retrieve(self, question: str) -> dict:
        cfg = self.config.get("retrieval", {})
        neo_cfg = self.config.get("neo4j", {})
        qu = understand_query(question, llm=self.llm, config=self.config)
        query_texts = self._query_texts(qu)

        chunk_vec_lists: list[list[dict]] = []
        entity_vec_lists: list[list[dict]] = []
        community_vec_lists: list[list[dict]] = []
        entity_kw_lists: list[list[dict]] = []
        chunks_kw_lists: list[list[dict]] = []

        for q in query_texts:
            q_emb = self.embedding_model.embed_query(q)
            community_vec_lists.append(self.store.vector_search(
                "Community", neo_cfg.get("community_vector_index", "community_embedding_index"), q_emb, int(cfg.get("top_k_communities", 5))
            ))
            chunk_vec_lists.append(self.store.vector_search(
                "Chunk", neo_cfg.get("chunk_vector_index", "chunk_embedding_index"), q_emb, int(cfg.get("top_k_chunks", 8))
            ))
            entity_vec_lists.append(self.store.vector_search(
                "Entity", neo_cfg.get("entity_vector_index", "entity_embedding_index"), q_emb, int(cfg.get("top_k_entities", 10))
            ))
            chunks_kw_lists.append(self.store.fulltext_search_chunks(q, int(cfg.get("top_k_chunks", 8))))
            try:
                entity_kw_lists.append(self.store.fulltext_search_entities(q, int(cfg.get("top_k_entities", 10))))
            except Exception:
                pass

        communities = self._rrf_fuse(community_vec_lists)[: int(cfg.get("top_k_communities", 5))]
        entities = self._rrf_fuse(entity_vec_lists + entity_kw_lists)[: int(cfg.get("top_k_entities", 10))]

        entity_keys = [x.get("node", {}).get("key") for x in entities if x.get("node", {}).get("key")]
        entity_name_keys = [str(e).strip().lower() for e in qu.entities if str(e).strip()]
        entity_chunk_results = self.store.chunks_mentioning_entities(
            entity_keys + entity_name_keys,
            limit=int(cfg.get("top_k_entity_linked_chunks", 10)),
        ) if (entity_keys or entity_name_keys) else []

        fused_chunks = self._rrf_fuse(chunk_vec_lists + chunks_kw_lists + [entity_chunk_results])
        fused_chunks = self._filter_chunks_by_page(fused_chunks, qu)
        final_chunks = fused_chunks[: int(cfg.get("final_context_chunks", 10))]

        paths = self.store.expand_from_entities(
            entity_keys,
            depth=int(cfg.get("graph_expand_depth", 2)),
            limit=int(cfg.get("graph_expand_limit", 30)),
        ) if entity_keys else []

        return {
            "query_understanding": qu.to_dict(),
            "query_texts": query_texts,
            "communities": communities,
            "chunks": final_chunks,
            "entities": entities,
            "graph_paths": paths,
        }

    @staticmethod
    def _page_label(node: dict) -> str:
        page_start = (
            node.get("page_start")
            or node.get("page")
            or node.get("page_number")
            or node.get("source_page")
            or node.get("book_page")
        )
        page_end = (
            node.get("page_end")
            or node.get("page")
            or node.get("page_number")
            or node.get("source_page")
            or node.get("book_page")
        )

        if page_start and page_end and str(page_start) != str(page_end):
            return f"trang {page_start}-{page_end}"
        if page_start:
            return f"trang {page_start}"
        return ""

    @staticmethod
    def _compact(text: str, max_chars: int = 2200) -> str:
        text = " ".join((text or "").split())
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip() + "..."

    def build_context(self, retrieved: dict) -> str:
        """
        Build context cho LLM nhưng không để lộ nhãn nội bộ như Chunk 1,
        Relevant entities, Community, score...
        Người dùng cuối chỉ được thấy nguồn theo trang.
        """
        lines = []
        qu = retrieved.get("query_understanding", {})

        lines.append("# Hướng hiểu câu hỏi, không dùng phần này làm nguồn trích dẫn")
        if qu.get("intent"):
            lines.append(f"- Mục đích: {qu.get('intent')}")
        if qu.get("rewritten_query"):
            lines.append(f"- Câu hỏi đã làm rõ: {qu.get('rewritten_query')}")
        if qu.get("sub_queries"):
            lines.append("- Các ý nhỏ cần trả lời:")
            for q in qu.get("sub_queries", []):
                lines.append(f"  - {q}")
        if qu.get("entities"):
            lines.append(f"- Khái niệm được nhận diện: {', '.join(qu.get('entities', []))}")
        if qu.get("keywords"):
            lines.append(f"- Từ khóa: {', '.join(qu.get('keywords', []))}")

        if retrieved.get("communities"):
            lines.append("\n# Tri thức tổng hợp theo cụm, chỉ dùng để hiểu ngữ cảnh, không trích dẫn")
            for item in retrieved.get("communities", []):
                n = item.get("node", {})
                title = n.get("title") or "Cụm kiến thức"
                summary = self._compact(n.get("summary", ""), max_chars=900)
                if summary:
                    lines.append(f"- {title}: {summary}")

        if retrieved.get("entities"):
            lines.append("\n# Khái niệm liên quan, chỉ dùng để hiểu ngữ nghĩa, không trích dẫn")
            for item in retrieved.get("entities", [])[:12]:
                n = item.get("node", {})
                name = n.get("name") or n.get("key", "")
                typ = n.get("type") or "Khái niệm"
                sem = self._compact(
                    n.get("semantic_summary") or n.get("description") or "",
                    max_chars=450
                )
                if name:
                    lines.append(f"- {name} ({typ}): {sem}")

        lines.append("\n# Trích đoạn từ sách được phép trích dẫn")
        for item in retrieved.get("chunks", []):
            n = item.get("node", {})
            page = self._page_label(n)
            heading = n.get("heading_path") or ""
            text = self._compact(n.get("text", ""), max_chars=1800)

            if page:
                lines.append(f"[Nguồn: {page}]")
            if heading:
                lines.append(f"Mục: {heading}")
            lines.append(f"Nội dung: {text}")

        if retrieved.get("graph_paths"):
            lines.append("\n# Quan hệ đồ thị liên quan, chỉ dùng để hiểu thêm, không trích dẫn")
            for p in retrieved.get("graph_paths", [])[:12]:
                path = " -> ".join(p.get("path", []))
                rel = " / ".join(p.get("relations", []))
                if path:
                    lines.append(f"- {path} ({rel})")

        return "\n\n".join(lines)

    @staticmethod
    def _clean_answer_for_user(answer: str) -> str:
        """
        Chuẩn hóa output cuối cùng trước khi in ra terminal:
        - Xóa nguồn nội bộ.
        - Xóa "(không rõ trang)".
        - Xóa dấu LaTeX $...$.
        - Chuyển một số LaTeX phổ biến sang text dễ đọc.
        - Xóa câu chào và câu mở đầu thừa.
        """
        if not answer:
            return answer

        text = answer.strip()

        text = re.sub(r"^\s*Chào bạn[,!.\s]*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^\s*Dưới đây là\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^\s*Về câu hỏi của bạn[^.\n]*[.\n]\s*", "", text, flags=re.IGNORECASE)

        internal_labels = r"Chunk|Relevant entities|Relevant chunks|Graph paths|Community|score|context"
        text = re.sub(
            rf"\(\s*Nguồn\s*:\s*(?:{internal_labels})[^)]*\)",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            rf"\(\s*(?:{internal_labels})[^)]*\)",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            rf"Nguồn\s*:\s*(?:{internal_labels})[^\n]*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\bChunk\s*\d+\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bRelevant entities\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bRelevant chunks\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bGraph paths\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bCommunity\b", "", text, flags=re.IGNORECASE)

        text = text.replace("(Nguồn: không rõ trang)", "")
        text = text.replace("[Nguồn: không rõ trang]", "")
        text = text.replace("(không rõ trang)", "")
        text = text.replace("[không rõ trang]", "")
        text = text.replace("không rõ trang", "")

        text = text.replace("$$", "")
        text = text.replace("$", "")
        text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"\1/\2", text)
        text = re.sub(r"([A-Za-z0-9)\]])\^\{([^{}]+)\}", r"\1^\2", text)
        text = re.sub(r"([A-Za-z0-9)\]])_\{([^{}]+)\}", r"\1_\2", text)

        replacements = {
            r"\mathbb{R}": "R",
            r"\mathbb{C}": "C",
            r"\int": "tích phân",
            r"\in": "thuộc",
            r"\subset": "là tập con của",
            r"\Delta": "Δ",
            r"\to": "→",
            r"\lim": "lim",
            r"\infty": "∞",
            r"\sqrt": "√",
            r"\frac": "",
            r"\cdot": ".",
            r"\times": "×",
            r"\leq": "≤",
            r"\geq": "≥",
            r"\neq": "≠",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        text = re.sub(r"\(\s*\)", "", text)
        text = re.sub(r"\[\s*\]", "", text)
        text = re.sub(r"\(\s*Nguồn\s*:\s*\)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\[\s*Nguồn\s*:\s*\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+([,.!?;:])", r"\1", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)

        return text.strip()

    def answer(self, question: str) -> dict:
        retrieved = self.retrieve(question)
        context = self.build_context(retrieved)
        prompt = ANSWER_PROMPT.format(question=question, context=context)
        answer = self._clean_answer_for_user(self.llm.invoke(prompt))

        sources = []
        for item in retrieved.get("chunks", []):
            n = item.get("node", {})
            sources.append({
                "id": n.get("id"),
                "heading_path": n.get("heading_path"),
                "page_start": n.get("page_start"),
                "page_end": n.get("page_end"),
                "score": item.get("fused_score", item.get("score")),
                "text_preview": (n.get("text") or "")[:300],
            })

        graph_paths = []
        for p in retrieved.get("graph_paths", [])[:10]:
            graph_paths.append({
                "path": p.get("path", []),
                "relation": " / ".join(p.get("relations", [])),
            })

        return {
            "question": question,
            "query_understanding": retrieved.get("query_understanding", {}),
            "query_texts": retrieved.get("query_texts", []),
            "answer": answer,
            "sources": sources,
            "graph_paths": graph_paths,
        }

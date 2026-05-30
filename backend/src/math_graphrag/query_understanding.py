from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any

from .prompts import QUERY_UNDERSTANDING_PROMPT

PAGE_PATTERNS = [
    re.compile(r"\btrang\s*(\d{1,4})(?:\s*[-–]\s*(\d{1,4}))?", re.I),
    re.compile(r"\bpage\s*(\d{1,4})(?:\s*[-–]\s*(\d{1,4}))?", re.I),
]
MATH_KEYWORD_RE = re.compile(
    r"[A-Za-zÀ-ỹ0-9]+(?:[\-_/][A-Za-zÀ-ỹ0-9]+)*|[+\-*/=<>≤≥∈∉∞√παβγΔ∫Σ]+",
    re.UNICODE,
)
STOPWORDS = {
    "là", "gì", "nào", "hãy", "cho", "tôi", "em", "anh", "chị", "bạn", "của", "về", "trong", "ở",
    "thì", "và", "hoặc", "một", "các", "những", "này", "kia", "đó", "được", "không", "có", "sao",
    "giải", "thích", "trình", "bày", "tính", "tìm", "nêu", "viết", "theo", "từ", "đến", "phần",
}
DECOMPOSE_SPLIT_RE = re.compile(r"\s+(?:và|rồi|sau đó|tiếp theo|đồng thời|so sánh với|khác gì|liên hệ với)\s+", re.I)


@dataclass
class QueryUnderstanding:
    original_question: str
    rewritten_query: str
    intent: str = "explain"
    entities: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    query_variants: list[str] = field(default_factory=list)
    sub_queries: list[str] = field(default_factory=list)
    answer_style: str = "ngắn gọn, dễ hiểu"
    page_start: int | None = None
    page_end: int | None = None
    book_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def _unique_keep_order(values: list[str], max_items: int = 12) -> list[str]:
    seen = set()
    out: list[str] = []
    for v in values:
        v = str(v).strip(" \n\t-•")
        if not v:
            continue
        key = v.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
        if len(out) >= max_items:
            break
    return out


def _extract_page_filter(question: str) -> tuple[int | None, int | None]:
    for pattern in PAGE_PATTERNS:
        m = pattern.search(question)
        if m:
            start = int(m.group(1))
            end = int(m.group(2) or start)
            if end < start:
                start, end = end, start
            return start, end
    return None, None


def _fallback_decompose(question: str, rewritten: str) -> list[str]:
    parts = [p.strip(" ,.;") for p in DECOMPOSE_SPLIT_RE.split(question) if p.strip(" ,.;")]
    good = [p for p in parts if len(p) >= 8]
    if 2 <= len(good) <= 5:
        return _unique_keep_order(good + [rewritten], max_items=5)
    return _unique_keep_order([rewritten, question], max_items=3)


def fallback_understand_query(question: str, config: dict | None = None) -> QueryUnderstanding:
    page_start, page_end = _extract_page_filter(question)
    tokens = MATH_KEYWORD_RE.findall(question)
    keywords = [t for t in tokens if len(t) > 1 and t.lower() not in STOPWORDS]
    keywords = _unique_keep_order(keywords, max_items=12)
    lowered = question.lower()

    entity_candidates: list[str] = []
    phrase_patterns = [
        r"(?:đạo hàm|nguyên hàm|tích phân|hàm số|cực trị|tiệm cận|đồng biến|nghịch biến|logarit|số phức|mũ|phương trình|bất phương trình|khảo sát hàm số)[^,.?;]*",
        r"(?:công thức|định nghĩa|định lý|hệ quả|phương pháp|dạng bài|tính chất|điều kiện)[^,.?;]*",
    ]
    for pat in phrase_patterns:
        for m in re.finditer(pat, lowered, flags=re.I):
            phrase = question[m.start():m.end()].strip()
            if 2 <= len(phrase) <= 100:
                entity_candidates.append(phrase)

    rewritten = " ".join(keywords) if keywords else question
    sub_queries = _fallback_decompose(question, rewritten)
    variants = _unique_keep_order([rewritten, *sub_queries, " ".join(entity_candidates + keywords)], max_items=6)
    return QueryUnderstanding(
        original_question=question,
        rewritten_query=rewritten or question,
        intent="solve" if any(w in lowered for w in ["giải", "tính", "tìm", "chứng minh"]) else ("compare" if "so sánh" in lowered or "khác" in lowered else "explain"),
        entities=_unique_keep_order(entity_candidates + keywords[:5], max_items=8),
        keywords=keywords,
        query_variants=variants,
        sub_queries=sub_queries,
        page_start=page_start,
        page_end=page_end,
        book_name=(config or {}).get("project", {}).get("book_name"),
    )


def understand_query(question: str, llm=None, config: dict | None = None) -> QueryUnderstanding:
    base = fallback_understand_query(question, config=config)
    use_llm = bool((config or {}).get("retrieval", {}).get("use_llm_query_understanding", True))
    if not llm or not use_llm:
        return base
    try:
        prompt = QUERY_UNDERSTANDING_PROMPT.format(question=question)
        data = _extract_json(llm.invoke(prompt))
        rewritten = str(data.get("rewritten_query") or base.rewritten_query or question).strip()
        intent = str(data.get("intent") or base.intent).strip() or "explain"
        entities = _unique_keep_order([str(x) for x in data.get("entities", [])] + base.entities, max_items=12)
        keywords = _unique_keep_order([str(x) for x in data.get("keywords", [])] + base.keywords, max_items=14)
        sub_queries = _unique_keep_order([str(x) for x in data.get("sub_queries", [])] + base.sub_queries + [rewritten], max_items=6)
        variants = _unique_keep_order([str(x) for x in data.get("query_variants", [])] + [rewritten, *sub_queries, question] + base.query_variants, max_items=8)
        filters = data.get("filters") or {}
        page_start = filters.get("page_start", base.page_start)
        page_end = filters.get("page_end", base.page_end)
        try:
            page_start = int(page_start) if page_start is not None else None
            page_end = int(page_end) if page_end is not None else None
        except Exception:
            page_start, page_end = base.page_start, base.page_end
        return QueryUnderstanding(
            original_question=question,
            rewritten_query=rewritten,
            intent=intent,
            entities=entities,
            keywords=keywords,
            query_variants=variants,
            sub_queries=sub_queries,
            answer_style=str(data.get("answer_style") or base.answer_style),
            page_start=page_start,
            page_end=page_end,
            book_name=str(filters.get("book_name") or base.book_name or "") or None,
        )
    except Exception:
        return base

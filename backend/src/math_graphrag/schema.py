from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal


@dataclass
class MathChunk:
    id: str
    text: str
    book_name: str
    heading_path: str = ""
    page_start: int | None = None
    page_end: int | None = None
    order: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def citation(self) -> str:
        if self.page_start and self.page_end and self.page_start != self.page_end:
            return f"{self.book_name}, trang {self.page_start}-{self.page_end}"
        if self.page_start:
            return f"{self.book_name}, trang {self.page_start}"
        return self.book_name

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Entity:
    """
    Node trong knowledge graph.

    type: loại node có kiểm soát tương đối, ví dụ Concept, Formula, Theorem, Method,
          ProblemType, Condition, Property, Example, Section.
    semantic_summary: ý nghĩa/ngữ cảnh của node trong sách, không chỉ là mô tả ngắn.
    definition: định nghĩa/công thức nếu chunk có nói rõ.
    properties: metadata mở rộng để lưu ký hiệu, điều kiện áp dụng, lớp/chương,...
    """
    name: str
    type: str = "Concept"
    description: str = ""
    semantic_summary: str = ""
    definition: str = ""
    aliases: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    @property
    def normalized_name(self) -> str:
        return " ".join(self.name.strip().lower().split())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Relationship:
    source: str
    target: str
    type: str = "RELATED_TO"
    description: str = ""
    semantic: str = ""
    evidence: str = ""
    weight: float = 1.0
    source_chunk_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphExtraction:
    chunk_id: str
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "entities": [x.to_dict() for x in self.entities],
            "relationships": [x.to_dict() for x in self.relationships],
        }


@dataclass
class CommunityRecord:
    id: str
    level: int
    title: str
    summary: str = ""
    entity_names: list[str] = field(default_factory=list)
    parent_id: str | None = None
    child_ids: list[str] = field(default_factory=list)
    relationship_summaries: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalItem:
    id: str
    kind: Literal["chunk", "entity", "community", "path"]
    text: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

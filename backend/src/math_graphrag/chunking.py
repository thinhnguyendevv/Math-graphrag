from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .schema import MathChunk
from .utils import read_text

PAGE_RE = re.compile(r"<!--\s*page\s*:\s*(\d+)\s*-->", re.I)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"!?\[[^\]]*\]\([^)]*\)")
FORMULA_RE = re.compile(r"(\$\$?|\\\(|\\\[|\\begin\{|=|≤|≥|∈|∀|∃|lim|sin|cos|tan|log|ln|sqrt|frac)", re.I)
LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
TABLE_RE = re.compile(r"^\s*\|.+\|\s*$")


def _chunk_id(book_name: str, order: int, text: str) -> str:
    h = hashlib.sha1(f"{book_name}:{order}:{text[:120]}".encode("utf-8")).hexdigest()[:12]
    return f"chunk_{order:06d}_{h}"


@dataclass
class HybridBlock:
    text: str
    heading_path: str
    page_start: int | None = None
    page_end: int | None = None
    kind: str = "paragraph"


def _page_text(page_start: int | None, page_end: int | None) -> str:
    if page_start and page_end and page_start != page_end:
        return f"trang {page_start}-{page_end}"
    if page_start:
        return f"trang {page_start}"
    return ""


def _kind_for_block(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "empty"
    if HEADING_RE.match(stripped.splitlines()[0]):
        return "heading"
    if TABLE_RE.match(stripped.splitlines()[0]):
        return "table"
    if LIST_RE.match(stripped.splitlines()[0]):
        return "list"
    if IMAGE_RE.search(stripped):
        return "image_or_caption"
    if FORMULA_RE.search(stripped):
        return "formula"
    return "paragraph"


def _infer_pages(lines: Iterable[str], current_page: int | None) -> tuple[int | None, int | None]:
    page_start = None
    page_end = None
    for line in lines:
        m = PAGE_RE.search(line)
        if m:
            page = int(m.group(1))
            page_start = page if page_start is None else min(page_start, page)
            page_end = page if page_end is None else max(page_end, page)
    if page_start is None:
        page_start = current_page
    if page_end is None:
        page_end = current_page
    return page_start, page_end


def split_with_overlap(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Split long text while trying to keep paragraph/sentence/formula boundaries."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        window = text[start:end]
        boundary_candidates = [
            window.rfind("\n\n"),
            window.rfind("\n#"),
            window.rfind(". "),
            window.rfind("; "),
            window.rfind("\n- "),
            window.rfind("\n1."),
        ]
        cut = max(boundary_candidates)
        if cut > max_chars * 0.5 and end < len(text):
            end = start + cut + 1
        parts.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap_chars)
    return [p for p in parts if p]


def _parse_markdown_blocks(text: str) -> list[HybridBlock]:
    """
    Parse markdown into small logical blocks.

    Hybrid nghĩa là giữ cấu trúc sách toán theo heading/page, nhưng đơn vị nhỏ bên trong
    vẫn tôn trọng paragraph, list, bảng và công thức. Sau đó các block được gom lại theo
    budget ký tự để tránh chunk quá ngắn hoặc quá dài.
    """
    current_page: int | None = None
    heading_stack: dict[int, str] = {}
    blocks: list[HybridBlock] = []
    buffer: list[str] = []
    buffer_kind: str | None = None
    buffer_page_start: int | None = None
    buffer_page_end: int | None = None

    def heading_path() -> str:
        return " > ".join(heading_stack[i] for i in sorted(heading_stack))

    def flush() -> None:
        nonlocal buffer, buffer_kind, buffer_page_start, buffer_page_end
        body = "\n".join(buffer).strip()
        if body:
            blocks.append(
                HybridBlock(
                    text=body,
                    heading_path=heading_path(),
                    page_start=buffer_page_start,
                    page_end=buffer_page_end,
                    kind=buffer_kind or _kind_for_block(body),
                )
            )
        buffer = []
        buffer_kind = None
        buffer_page_start = None
        buffer_page_end = None

    def add_line_to_buffer(line: str, kind: str) -> None:
        nonlocal buffer_kind, buffer_page_start, buffer_page_end
        if buffer_kind is None:
            buffer_kind = kind
        buffer.append(line)
        page_start, page_end = _infer_pages([line], current_page)
        if page_start is not None:
            buffer_page_start = page_start if buffer_page_start is None else min(buffer_page_start, page_start)
        if page_end is not None:
            buffer_page_end = page_end if buffer_page_end is None else max(buffer_page_end, page_end)

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        pm = PAGE_RE.search(line)
        if pm:
            current_page = int(pm.group(1))
            flush()
            blocks.append(HybridBlock(text=line, heading_path=heading_path(), page_start=current_page, page_end=current_page, kind="page_marker"))
            continue

        hm = HEADING_RE.match(line)
        if hm:
            flush()
            level = len(hm.group(1))
            title = hm.group(2).strip()
            heading_stack = {k: v for k, v in heading_stack.items() if k < level}
            heading_stack[level] = title
            blocks.append(HybridBlock(text=line, heading_path=heading_path(), page_start=current_page, page_end=current_page, kind="heading"))
            continue

        if not line.strip():
            flush()
            continue

        kind = _kind_for_block(line)
        # Tables/lists/formulas often span multiple consecutive lines. Keep same kind together.
        if buffer and buffer_kind not in {kind, "formula", "list", "table"}:
            flush()
        if buffer and kind in {"paragraph", "image_or_caption"} and buffer_kind != kind:
            flush()
        add_line_to_buffer(line, kind)

    flush()
    return [b for b in blocks if b.text.strip()]


def _merge_blocks_to_chunks(blocks: list[HybridBlock], book_name: str, config: dict) -> list[MathChunk]:
    ch_cfg = config.get("chunking", {})
    max_chars = int(ch_cfg.get("max_chars", 1400))
    overlap_chars = int(ch_cfg.get("overlap_chars", 180))
    min_chars = int(ch_cfg.get("min_chars", 150))
    soft_max_chars = int(ch_cfg.get("soft_max_chars", max_chars))
    keep_heading_context = bool(ch_cfg.get("keep_heading_context", True))

    chunks: list[MathChunk] = []
    order = 0
    current: list[HybridBlock] = []
    current_len = 0

    def make_chunk(block_group: list[HybridBlock]) -> None:
        nonlocal order
        if not block_group:
            return
        text = "\n".join(b.text for b in block_group if b.kind != "page_marker").strip()
        if not text:
            return
        page_start_vals = [b.page_start for b in block_group if b.page_start is not None]
        page_end_vals = [b.page_end for b in block_group if b.page_end is not None]
        page_start = min(page_start_vals) if page_start_vals else None
        page_end = max(page_end_vals) if page_end_vals else None
        heading = next((b.heading_path for b in reversed(block_group) if b.heading_path), "")
        kinds = sorted({b.kind for b in block_group if b.kind != "page_marker"})
        prefix = ""
        if keep_heading_context and heading and not text.startswith("#"):
            page_label = _page_text(page_start, page_end)
            prefix = f"[Mục: {heading}]\n"
            if page_label:
                prefix += f"[Trang: {page_label}]\n"
        full_text = (prefix + text).strip()

        for part in split_with_overlap(full_text, max_chars=max_chars, overlap_chars=overlap_chars):
            if len(part) < min_chars and chunks:
                chunks[-1].text += "\n\n" + part
                if page_end:
                    chunks[-1].page_end = page_end
                chunks[-1].metadata.setdefault("merged_small_chunk", True)
                continue
            order += 1
            chunks.append(
                MathChunk(
                    id=_chunk_id(book_name, order, part),
                    text=part,
                    book_name=book_name,
                    heading_path=heading,
                    page_start=page_start,
                    page_end=page_end,
                    order=order,
                    metadata={
                        "chunk_strategy": "hybrid",
                        "block_kinds": kinds,
                        "char_len": len(part),
                    },
                )
            )

    for block in blocks:
        # Page markers only carry page metadata and should not force noisy standalone chunks.
        if block.kind == "page_marker":
            if current:
                current.append(block)
            continue

        block_len = len(block.text)
        force_new = False
        if current:
            last_heading = next((b.heading_path for b in reversed(current) if b.heading_path), "")
            # Start a new chunk at a new major heading, except when current is too tiny.
            if block.kind == "heading" and current_len >= min_chars:
                force_new = True
            elif last_heading != block.heading_path and current_len >= min_chars:
                force_new = True
            elif current_len + block_len > soft_max_chars:
                force_new = True

        if force_new:
            make_chunk(current)
            current = []
            current_len = 0

        # Very long block gets split immediately.
        if block_len > max_chars:
            if current:
                make_chunk(current)
                current = []
                current_len = 0
            make_chunk([block])
            continue

        current.append(block)
        current_len += block_len + 1

    if current:
        make_chunk(current)

    return chunks


def _legacy_chunk_markdown_text(text: str, book_name: str, config: dict) -> list[MathChunk]:
    """Old heading-based chunker kept for reproducibility."""
    ch_cfg = config.get("chunking", {})
    max_chars = int(ch_cfg.get("max_chars", 1400))
    overlap_chars = int(ch_cfg.get("overlap_chars", 180))
    min_chars = int(ch_cfg.get("min_chars", 150))

    current_page: int | None = None
    heading_stack: dict[int, str] = {}
    section_lines: list[str] = []
    section_page_start: int | None = None
    section_page_end: int | None = None
    sections: list[tuple[str, str, int | None, int | None]] = []

    def flush():
        nonlocal section_lines, section_page_start, section_page_end
        body = "\n".join(section_lines).strip()
        if body:
            heading_path = " > ".join(heading_stack[i] for i in sorted(heading_stack))
            sections.append((heading_path, body, section_page_start, section_page_end))
        section_lines = []
        section_page_start = None
        section_page_end = None

    for line in text.splitlines():
        pm = PAGE_RE.search(line)
        if pm:
            current_page = int(pm.group(1))
            if section_page_start is None:
                section_page_start = current_page
            section_page_end = current_page
            section_lines.append(line)
            continue

        hm = HEADING_RE.match(line)
        if hm:
            flush()
            level = len(hm.group(1))
            title = hm.group(2).strip()
            heading_stack = {k: v for k, v in heading_stack.items() if k < level}
            heading_stack[level] = title
            section_page_start = current_page
            section_page_end = current_page
            section_lines.append(line)
        else:
            if line.strip() and section_page_start is None:
                section_page_start = current_page
            if line.strip() and current_page is not None:
                section_page_end = current_page
            section_lines.append(line)

    flush()

    chunks: list[MathChunk] = []
    order = 0
    for heading_path, body, page_start, page_end in sections:
        for part in split_with_overlap(body, max_chars=max_chars, overlap_chars=overlap_chars):
            if len(part) < min_chars and chunks:
                chunks[-1].text += "\n\n" + part
                if page_end:
                    chunks[-1].page_end = page_end
                continue
            order += 1
            chunks.append(
                MathChunk(
                    id=_chunk_id(book_name, order, part),
                    text=part,
                    book_name=book_name,
                    heading_path=heading_path,
                    page_start=page_start,
                    page_end=page_end,
                    order=order,
                    metadata={"chunk_strategy": "heading_legacy"},
                )
            )
    return chunks


def chunk_markdown_text(text: str, book_name: str, config: dict) -> list[MathChunk]:
    mode = str(config.get("chunking", {}).get("mode", "hybrid")).lower()
    if mode in {"heading", "legacy", "structure"}:
        return _legacy_chunk_markdown_text(text, book_name=book_name, config=config)
    blocks = _parse_markdown_blocks(text)
    return _merge_blocks_to_chunks(blocks, book_name=book_name, config=config)


def chunk_markdown_file(path: str | Path, config: dict, book_name: str | None = None) -> list[MathChunk]:
    book_name = book_name or config.get("project", {}).get("book_name") or Path(path).stem
    return chunk_markdown_text(read_text(path), book_name=book_name, config=config)

from __future__ import annotations

import re
from pathlib import Path

from .utils import normalize_vi_text, read_text, write_text, ensure_dir

PAGE_PATTERNS = [
    re.compile(r"<!--\s*page\s*[:=]\s*(\d+)\s*-->", re.I),
    re.compile(r"^\s*[-–—]*\s*Page\s+(\d+)\s*[-–—]*\s*$", re.I | re.M),
    re.compile(r"^\s*[-–—]*\s*Trang\s+(\d+)\s*[-–—]*\s*$", re.I | re.M),
]

COMMON_OCR_FIXES = {
    "Dạo hàm": "Đạo hàm",
    "dạo hàm": "đạo hàm",
    "dạo hảm": "đạo hàm",
    "hàm sô": "hàm số",
    "tiệm cân": "tiệm cận",
    "cưc trị": "cực trị",
    "đông biến": "đồng biến",
    "nghich biến": "nghịch biến",
}


def standardize_page_markers(text: str) -> str:
    for pat in PAGE_PATTERNS[1:]:
        text = pat.sub(lambda m: f"\n<!-- page: {m.group(1)} -->\n", text)
    text = PAGE_PATTERNS[0].sub(lambda m: f"\n<!-- page: {m.group(1)} -->\n", text)
    return text


def normalize_headings(text: str) -> str:
    lines = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            lines.append("")
            continue
        if re.match(r"^(CHƯƠNG|Chương)\s*[IVXLCDM0-9]+", raw):
            raw = re.sub(r"^(#+\s*)?", "# ", raw)
        elif re.match(r"^(BÀI|Bài)\s*\d+", raw):
            raw = re.sub(r"^(#+\s*)?", "## ", raw)
        elif re.match(r"^\d+\.\s+", raw) and len(raw) < 120:
            raw = re.sub(r"^(#+\s*)?", "### ", raw)
        lines.append(raw)
    return "\n".join(lines)


def preprocess_markdown_text(text: str, *, remove_image_links: bool = False, fix_common_ocr_errors: bool = True) -> str:
    text = normalize_vi_text(text)
    text = standardize_page_markers(text)

    if remove_image_links:
        text = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", text)

    # Fix broken spaces around common math symbols but do not rewrite formulas aggressively.
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([([{])\s+", r"\1", text)
    text = re.sub(r"\s+([)\]}])", r"\1", text)
    text = re.sub(r"\blim\s+", "lim ", text)

    if fix_common_ocr_errors:
        for wrong, right in COMMON_OCR_FIXES.items():
            text = text.replace(wrong, right)

    text = normalize_headings(text)
    text = normalize_vi_text(text)
    return text


def preprocess_file(input_path: str | Path, output_path: str | Path, config: dict | None = None) -> Path:
    config = config or {}
    pp_cfg = config.get("preprocess", {})
    raw = read_text(input_path)
    clean = preprocess_markdown_text(
        raw,
        remove_image_links=bool(pp_cfg.get("remove_image_links", False)),
        fix_common_ocr_errors=bool(pp_cfg.get("fix_common_ocr_errors", True)),
    )
    write_text(output_path, clean)
    return Path(output_path)


def preprocess_directory(input_dir: str | Path, output_dir: str | Path, config: dict | None = None) -> list[Path]:
    input_dir = Path(input_dir)
    output_dir = ensure_dir(output_dir)
    outputs = []
    for path in sorted(input_dir.glob("*.md")):
        out = output_dir / path.name
        outputs.append(preprocess_file(path, out, config))
    return outputs

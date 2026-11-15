"""Structure-first sectioning with paragraph-aggregation fallback."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Target size for prose aggregation (characters).
SECTION_MIN_CHARS = 800
SECTION_MAX_CHARS = 1500

_HEADING_RE = re.compile(
    r"^(?:"
    r"#{1,6}\s+.+"  # markdown headings
    r"|第[零一二三四五六七八九十百千0-9]+[章节篇部]\s*.*"  # 第x章/节
    r"|Chapter\s+\d+\b.*"
    r")$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class SectionDraft:
    title: str
    body: str
    ordinal: int
    source_span: str | None = None


def _is_heading_line(line: str) -> bool:
    text = (line or "").strip()
    if not text:
        return False
    if text.startswith("#"):
        return bool(re.match(r"^#{1,6}\s+\S", text))
    if re.match(r"^第[零一二三四五六七八九十百千0-9]+[章节篇部]", text):
        return True
    if re.match(r"^Chapter\s+\d+\b", text, re.IGNORECASE):
        return True
    return False


def _clean_heading_title(line: str) -> str:
    text = (line or "").strip()
    text = re.sub(r"^#{1,6}\s+", "", text).strip()
    return text[:256] or "未命名章节"


def split_by_headings(text: str) -> list[SectionDraft] | None:
    """Return titled sections when recognizable headings exist; else None."""
    body = (text or "").replace("\r\n", "\n").strip()
    if not body:
        return None
    lines = body.split("\n")
    heading_idxs = [i for i, line in enumerate(lines) if _is_heading_line(line)]
    if not heading_idxs:
        return None

    sections: list[SectionDraft] = []
    # Optional preamble before first heading becomes its own section.
    if heading_idxs[0] > 0:
        preamble = "\n".join(lines[: heading_idxs[0]]).strip()
        if preamble:
            sections.append(
                SectionDraft(
                    title="引言",
                    body=preamble,
                    ordinal=0,
                    source_span=f"0:{heading_idxs[0]}",
                )
            )

    for hi, start in enumerate(heading_idxs):
        end = heading_idxs[hi + 1] if hi + 1 < len(heading_idxs) else len(lines)
        title = _clean_heading_title(lines[start])
        content = "\n".join(lines[start + 1 : end]).strip()
        if not content:
            content = title
        sections.append(
            SectionDraft(
                title=title,
                body=content,
                ordinal=len(sections),
                source_span=f"{start}:{end}",
            )
        )
    return sections or None


def split_by_paragraph_aggregation(
    text: str,
    *,
    min_chars: int = SECTION_MIN_CHARS,
    max_chars: int = SECTION_MAX_CHARS,
) -> list[SectionDraft]:
    """Aggregate paragraphs into ordered sections of roughly min–max chars."""
    body = (text or "").replace("\r\n", "\n").strip()
    if not body:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    if not paragraphs:
        paragraphs = [body]

    sections: list[SectionDraft] = []
    buf: list[str] = []
    buf_len = 0

    def flush() -> None:
        nonlocal buf, buf_len
        if not buf:
            return
        chunk = "\n\n".join(buf).strip()
        if not chunk:
            buf = []
            buf_len = 0
            return
        idx = len(sections) + 1
        sections.append(
            SectionDraft(
                title=f"第 {idx} 段",
                body=chunk,
                ordinal=len(sections),
                source_span=None,
            )
        )
        buf = []
        buf_len = 0

    for para in paragraphs:
        para_len = len(para)
        if buf and buf_len + para_len + 2 > max_chars and buf_len >= min_chars:
            flush()
        buf.append(para)
        buf_len += para_len + (2 if len(buf) > 1 else 0)
        if buf_len >= max_chars:
            flush()
    flush()
    return sections


def split_into_sections(text: str) -> list[SectionDraft]:
    """Structure-first; fall back to paragraph aggregation."""
    headed = split_by_headings(text)
    if headed:
        return headed
    return split_by_paragraph_aggregation(text)

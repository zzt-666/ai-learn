"""Extract key points from a section (LLM with heuristic fallback)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.services.llm import get_quiz_llm

logger = logging.getLogger(__name__)

POINTS_PER_SECTION_MIN = 2
POINTS_PER_SECTION_MAX = 8
_MAX_SECTION_CHARS = 4000


@dataclass(frozen=True)
class PointDraft:
    title: str
    summary: str
    keywords: list[str] | None = None


# Names must not start with "_" — DeepSeek/tool-calling strips the underscore in
# the returned tool type, and LangChain then fails to match `_LlmPointsOut`.
class LlmPoint(BaseModel):
    title: str = Field(description="短标题，不超过 40 字")
    summary: str = Field(description="1–3 句要点说明，作为出题依据")
    keywords: list[str] = Field(default_factory=list)


class LlmPointsOut(BaseModel):
    points: list[LlmPoint] = Field(default_factory=list)


def heuristic_extract_points(
    body: str,
    *,
    section_title: str = "",
    max_points: int = POINTS_PER_SECTION_MAX,
) -> list[PointDraft]:
    """Fallback: turn substantial sentences into points when LLM is unavailable."""
    text = (body or "").strip()
    if not text:
        return []
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[。！？；\n])", text)
        if s and s.strip() and len(s.strip()) >= 12
    ]
    if not sentences:
        title = (section_title or "要点").strip()[:40] or "要点"
        return [PointDraft(title=title, summary=text[:400], keywords=None)]

    out: list[PointDraft] = []
    step = max(1, len(sentences) // max_points) if len(sentences) > max_points else 1
    for i in range(0, len(sentences), step):
        if len(out) >= max_points:
            break
        chunk = "".join(sentences[i : i + step]).strip()
        if not chunk:
            continue
        title = chunk[:36].rstrip("，,；;：:") + ("…" if len(chunk) > 36 else "")
        out.append(PointDraft(title=title, summary=chunk[:500], keywords=None))
    if len(out) < POINTS_PER_SECTION_MIN and sentences:
        # Ensure at least one point covering the section.
        joined = "".join(sentences)[:500]
        title = (section_title or "本节要点").strip()[:40] or "本节要点"
        return [PointDraft(title=title, summary=joined, keywords=None)]
    return out


def llm_extract_points(
    body: str,
    *,
    section_title: str = "",
    max_points: int = POINTS_PER_SECTION_MAX,
) -> list[PointDraft]:
    """LLM structured extract; returns [] on failure (caller may fall back)."""
    text = (body or "").strip()
    if not text:
        return []
    clipped = text[:_MAX_SECTION_CHARS]
    try:
        llm = get_quiz_llm().with_structured_output(LlmPointsOut)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是学习要点提炼助手。从章节正文抽出可考查的知识点。"
                    f"每节约 {POINTS_PER_SECTION_MIN}–{max_points} 个要点；"
                    "每个要点含短标题与 1–3 句摘要；不要编造原文没有的内容；"
                    "摘要须足以据此出题。",
                ),
                (
                    "human",
                    "章节标题：{title}\n\n正文：\n{body}\n\n请输出 points 列表。",
                ),
            ]
        )
        result = (prompt | llm).invoke({"title": section_title or "未命名", "body": clipped})
    except Exception:  # noqa: BLE001
        logger.exception("llm point extract failed title=%s", section_title[:40])
        return []

    out: list[PointDraft] = []
    for raw in result.points or []:
        title = (raw.title or "").strip()[:256]
        summary = (raw.summary or "").strip()
        if not title or not summary:
            continue
        kws = [str(k).strip() for k in (raw.keywords or []) if str(k).strip()][:8]
        out.append(PointDraft(title=title, summary=summary[:800], keywords=kws or None))
        if len(out) >= max_points:
            break
    return out


def extract_points(
    body: str,
    *,
    section_title: str = "",
    max_points: int = POINTS_PER_SECTION_MAX,
    use_llm: bool = True,
) -> list[PointDraft]:
    if use_llm:
        points = llm_extract_points(body, section_title=section_title, max_points=max_points)
        if points:
            return points
    return heuristic_extract_points(
        body, section_title=section_title, max_points=max_points
    )

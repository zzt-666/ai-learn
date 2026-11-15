"""LLM-assisted question extraction when rule-based split finds nothing."""

from __future__ import annotations

import logging
import re

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.services.llm import get_quiz_llm
from app.services.question_split import ExtractedQuestion, looks_like_image_question

logger = logging.getLogger(__name__)

_MAX_CHARS = 6000
_MAX_BATCHES = 3


class _LlmQuestion(BaseModel):
    qtype: str = Field(description="single | multi | judge")
    stem: str
    options: list[str] = Field(default_factory=list)
    answer_indexes: list[int] = Field(default_factory=list)
    explanation: str | None = None


class _LlmSplitOut(BaseModel):
    questions: list[_LlmQuestion] = Field(default_factory=list)


def _chunk_text(text: str, *, max_chars: int = _MAX_CHARS) -> list[str]:
    body = (text or "").strip()
    if not body:
        return []
    if len(body) <= max_chars:
        return [body]
    parts: list[str] = []
    start = 0
    while start < len(body) and len(parts) < _MAX_BATCHES:
        end = min(len(body), start + max_chars)
        if end < len(body):
            # Prefer break near a blank line / question-ish boundary
            window = body[start:end]
            cut = max(window.rfind("\n\n"), window.rfind("\n【答案】"), window.rfind("\n答案"))
            if cut > max_chars // 3:
                end = start + cut
        parts.append(body[start:end].strip())
        start = end
    return [p for p in parts if p]


def _normalize_item(raw: _LlmQuestion) -> ExtractedQuestion | None:
    qtype = (raw.qtype or "").strip().lower()
    if qtype in {"multiple", "multi_choice", "多选"}:
        qtype = "multi"
    if qtype in {"boolean", "true_false", "判断"}:
        qtype = "judge"
    if qtype in {"single_choice", "单选"}:
        qtype = "single"
    if qtype not in {"single", "multi", "judge"}:
        return None
    stem = (raw.stem or "").strip()
    if not stem:
        return None
    options = [str(o).strip() for o in (raw.options or []) if str(o).strip()]
    answers = [int(i) for i in (raw.answer_indexes or []) if isinstance(i, int) or str(i).isdigit()]
    answers = [i for i in answers if 0 <= i < max(len(options), 2)]
    if qtype == "judge":
        if len(options) < 2:
            options = ["正确", "错误"]
        if not answers:
            return None
        answers = [answers[0]]
    else:
        if len(options) < 2 or not answers:
            return None
    if looks_like_image_question(stem) or any(looks_like_image_question(o) for o in options):
        return ExtractedQuestion(
            qtype=qtype,
            stem=stem,
            options=options,
            answer_indices=answers,
            explanation=(raw.explanation or None),
            confidence=0.4,
            looks_like_image=True,
        )
    return ExtractedQuestion(
        qtype=qtype,
        stem=stem,
        options=options,
        answer_indices=answers,
        explanation=(raw.explanation or None),
        confidence=0.7,
        looks_like_image=False,
    )


def llm_split_questions(text: str) -> list[ExtractedQuestion]:
    """Extract structured questions via LLM; returns [] on failure."""
    batches = _chunk_text(text)
    if not batches:
        return []
    llm = get_quiz_llm().with_structured_output(_LlmSplitOut)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是题库拆题助手。从给定文本中抽出单选/多选/判断题。"
                "忽略图片题、填空题、简答题。"
                "qtype 只能是 single、multi、judge；"
                "answer_indexes 为选项下标（从 0 开始）；"
                "judge 的 options 用 [正确, 错误]。"
                "不要编造原文没有的题目。",
            ),
            ("human", "文本：\n{chunk}\n\n请输出 questions 列表。"),
        ]
    )
    chain = prompt | llm
    out: list[ExtractedQuestion] = []
    seen: set[str] = set()
    for chunk in batches:
        try:
            result = chain.invoke({"chunk": chunk})
        except Exception:  # noqa: BLE001
            logger.exception("llm question split failed")
            continue
        for raw in result.questions or []:
            item = _normalize_item(raw)
            if item is None or item.looks_like_image:
                continue
            key = re.sub(r"\s+", "", item.stem)[:80]
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
    return out

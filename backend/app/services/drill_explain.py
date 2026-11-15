"""Lazy AI explanation for drill questions missing source explanation."""

from __future__ import annotations

import logging

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import KbQuestion
from app.services.llm import get_quiz_llm

logger = logging.getLogger(__name__)


class _ExplainOut(BaseModel):
    explanation: str = Field(min_length=1)


def ensure_ai_explanation(db: Session, *, question: KbQuestion) -> tuple[str, str]:
    """Return (explanation, source). Generate+cache when missing."""
    if question.explanation and question.explanation_source in {"source", "ai"}:
        return question.explanation, question.explanation_source

    options = question.options_json or []
    answers = question.answer_indices_json or []
    answer_text = ", ".join(
        options[i] for i in answers if isinstance(i, int) and 0 <= i < len(options)
    )
    llm = get_quiz_llm().with_structured_output(_ExplainOut)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是习题讲解助手。根据题干、选项与正确答案写简短中文解析（2-5句），不要编造与题目无关的考点。",
            ),
            (
                "human",
                "题型：{qtype}\n题干：{stem}\n选项：{options}\n正确答案：{answer}\n请输出 explanation。",
            ),
        ]
    )
    chain = prompt | llm
    result = chain.invoke(
        {
            "qtype": question.qtype,
            "stem": question.stem,
            "options": " / ".join(str(o) for o in options),
            "answer": answer_text or str(answers),
        }
    )
    text = (result.explanation or "").strip()
    if not text:
        text = "暂无解析"
    question.explanation = text
    question.explanation_source = "ai"
    db.commit()
    db.refresh(question)
    return question.explanation, question.explanation_source

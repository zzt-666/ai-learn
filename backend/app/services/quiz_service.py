import logging
from collections.abc import Callable

from langchain_core.prompts import ChatPromptTemplate

from app.models.quiz import QuizPayload
from app.services.llm import get_quiz_llm
from app.services.prompts import (
    QUIZ_HUMAN,
    QUIZ_HUMAN_GROUNDED,
    QUIZ_SYSTEM,
    QUIZ_SYSTEM_GROUNDED,
)
from app.services.quiz_research import gather_research_context
from app.services.quiz_validate import validate_quiz_mix
from app.services.tool_call_logging import preview_text

logger = logging.getLogger(__name__)

CancelCheck = Callable[[], bool]


class QuizTaskCancelled(Exception):
    """Raised when the user cancels an in-flight async quiz generation."""


def _raise_if_cancelled(should_cancel: CancelCheck | None) -> None:
    if should_cancel and should_cancel():
        raise QuizTaskCancelled()


def _build_quiz_chain(*, grounded: bool = False):
    llm = get_quiz_llm()
    if grounded:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", QUIZ_SYSTEM_GROUNDED),
                ("human", QUIZ_HUMAN_GROUNDED),
            ]
        )
    else:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", QUIZ_SYSTEM),
                ("human", QUIZ_HUMAN),
            ]
        )
    return prompt | llm.with_structured_output(QuizPayload)


def _invoke_quiz_chain(
    *,
    source_text: str,
    topic_name: str | None,
    question_count: int,
    research_context: str | None,
    should_cancel: CancelCheck | None = None,
) -> QuizPayload:
    grounded = bool(research_context)
    chain = _build_quiz_chain(grounded=grounded)
    inputs: dict = {
        "source_text": source_text,
        "topic_name": topic_name or "",
        "question_count": question_count,
    }
    if grounded:
        inputs["research_context"] = research_context

    last_error: Exception | None = None
    for attempt in range(2):
        _raise_if_cancelled(should_cancel)
        try:
            result = chain.invoke(inputs)
            if not isinstance(result, QuizPayload):
                result = QuizPayload.model_validate(result)
            if topic_name:
                result.topic_name = topic_name
            validate_quiz_mix(result, expected_count=question_count)
            return result
        except QuizTaskCancelled:
            raise
        except Exception as exc:  # noqa: BLE001 - 业务层统一包装
            last_error = exc
            if attempt == 0:
                _raise_if_cancelled(should_cancel)
                hint = (
                    "\n\n（请严格遵守题型字段与题量，至少包含单选与判断；"
                    "围绕主题出有区分度的题，禁止字面检索类弱题。"
                )
                if grounded:
                    hint += "优先依据联网参考内容。）"
                else:
                    hint += "围绕主题用你的已有知识出题。）"
                inputs = {
                    **inputs,
                    "source_text": source_text + hint,
                }
                continue
            break

    raise RuntimeError(f"出题失败：{last_error}")


def generate_quiz(
    source_text: str,
    topic_name: str | None,
    question_count: int,
    should_cancel: CancelCheck | None = None,
) -> QuizPayload:
    # Always attempt web grounding when enabled; failures degrade silently.
    logger.info(
        "quiz_generate=start topic=%s n=%s clue=%s",
        topic_name or "(auto)",
        question_count,
        preview_text(source_text, limit=80),
    )
    _raise_if_cancelled(should_cancel)
    research_context = gather_research_context(source_text)
    _raise_if_cancelled(should_cancel)
    grounded = bool(research_context)
    logger.info(
        "quiz_generate=mode grounded=%s research_chars=%s",
        grounded,
        len(research_context) if research_context else 0,
    )
    payload = _invoke_quiz_chain(
        source_text=source_text,
        topic_name=topic_name,
        question_count=question_count,
        research_context=research_context,
        should_cancel=should_cancel,
    )
    _raise_if_cancelled(should_cancel)
    logger.info(
        "quiz_generate=done grounded=%s topic=%s questions=%s",
        grounded,
        payload.topic_name,
        len(payload.questions),
    )
    return payload

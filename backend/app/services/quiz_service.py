import logging
from collections.abc import Callable

from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session

from app.models.quiz import QuizPayload
from app.services.llm import get_quiz_llm
from app.services.prompts import (
    QUIZ_HUMAN,
    QUIZ_HUMAN_GROUNDED,
    QUIZ_HUMAN_KB,
    QUIZ_SYSTEM,
    QUIZ_SYSTEM_GROUNDED,
    QUIZ_SYSTEM_KB,
)
from app.services.quiz_research import (
    KnowledgeBaseGroundingError,
    gather_research_context,
)
from app.services.quiz_validate import validate_quiz_mix
from app.services.tool_call_logging import preview_text

logger = logging.getLogger(__name__)

CancelCheck = Callable[[], bool]


class QuizTaskCancelled(Exception):
    """Raised when the user cancels an in-flight async quiz generation."""


def _raise_if_cancelled(should_cancel: CancelCheck | None) -> None:
    if should_cancel and should_cancel():
        raise QuizTaskCancelled()


def _build_quiz_chain(*, mode: str):
    """mode: model | web | kb"""
    llm = get_quiz_llm()
    if mode == "kb":
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", QUIZ_SYSTEM_KB),
                ("human", QUIZ_HUMAN_KB),
            ]
        )
    elif mode == "web":
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
    used_knowledge_base: bool,
    should_cancel: CancelCheck | None = None,
) -> QuizPayload:
    if research_context and used_knowledge_base:
        mode = "kb"
    elif research_context:
        mode = "web"
    else:
        mode = "model"
    chain = _build_quiz_chain(mode=mode)
    inputs: dict = {
        "source_text": source_text,
        "topic_name": topic_name or "",
        "question_count": question_count,
    }
    if mode in {"kb", "web"}:
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
                if mode == "kb":
                    hint += "优先依据知识库材料，少编造库外事实。）"
                elif mode == "web":
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
    *,
    db: Session | None = None,
    user_id: int | None = None,
    knowledge_base_id: int | None = None,
    drill_round: str | None = None,
) -> QuizPayload:
    logger.info(
        "quiz_generate=start topic=%s n=%s kb_id=%s round=%s clue=%s",
        topic_name or "(auto)",
        question_count,
        knowledge_base_id,
        drill_round,
        preview_text(source_text, limit=80),
    )
    _raise_if_cancelled(should_cancel)

    if knowledge_base_id is not None and db is not None and user_id is not None:
        from app.exceptions import bad_request
        from app.models.knowledge import KnowledgeBaseMode, MasterMapStatus
        from app.services.drill_service import assemble_quiz_payload, mark_practiced
        from app.services.knowledge_service import get_owned_base
        from app.services.master_map_service import (
            build_master_research_context,
            mark_points_seen,
            sample_points_for_round,
        )

        kb = get_owned_base(db, kb_id=knowledge_base_id, user_id=user_id)
        if kb.mode == KnowledgeBaseMode.drill.value:
            review = (drill_round or "").strip().lower() == "review"
            payload, rows = assemble_quiz_payload(
                db,
                kb=kb,
                user_id=user_id,
                question_count=question_count,
                review=review,
            )
            mark_practiced(
                db,
                user_id=user_id,
                kb_id=kb.id,
                question_ids=[q.id for q in rows],
            )
            _raise_if_cancelled(should_cancel)
            logger.info(
                "quiz_generate=done mode=drill topic=%s questions=%s",
                payload.topic_name,
                len(payload.questions),
            )
            return payload

        if kb.mode == KnowledgeBaseMode.master.value:
            map_status = (kb.master_map_status or "").strip().lower()
            review = (drill_round or "").strip().lower() == "review"
            if map_status == MasterMapStatus.ready.value:
                points, needs_review = sample_points_for_round(
                    db,
                    kb_id=kb.id,
                    user_id=user_id,
                    question_count=question_count,
                    review=review,
                )
                if needs_review and not review:
                    raise bad_request(
                        "MASTER_NEEDS_REVIEW",
                        "本库要点已过一轮，请选择复习轮或重置覆盖",
                    )
                if not points:
                    raise bad_request(
                        "MASTER_EMPTY",
                        "要点地图为空，请重建地图或换文档",
                    )
                research_context = build_master_research_context(
                    points=points,
                    kb_id=kb.id,
                    user_id=user_id,
                    supplement=True,
                )
                _raise_if_cancelled(should_cancel)
                # Use points summary as the grounded clue; avoid stuffing full doc.
                payload = _invoke_quiz_chain(
                    source_text=source_text,
                    topic_name=topic_name or kb.name,
                    question_count=question_count,
                    research_context=research_context,
                    used_knowledge_base=True,
                    should_cancel=should_cancel,
                )
                mark_points_seen(
                    db,
                    user_id=user_id,
                    kb_id=kb.id,
                    point_ids=[p.id for p in points],
                )
                _raise_if_cancelled(should_cancel)
                logger.info(
                    "quiz_generate=done mode=master_points topic=%s points=%s questions=%s",
                    payload.topic_name,
                    len(points),
                    len(payload.questions),
                )
                return payload
            # pending / failed / missing: degrade to legacy Top-K path (client warned via master-status).
            logger.info(
                "quiz_generate=master_degrade map_status=%s kb_id=%s",
                map_status or "none",
                kb.id,
            )

    try:
        research = gather_research_context(
            source_text,
            db=db,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
        )
    except KnowledgeBaseGroundingError:
        raise
    _raise_if_cancelled(should_cancel)
    logger.info(
        "quiz_generate=mode research=%s used_kb=%s research_chars=%s",
        research.mode,
        research.used_knowledge_base,
        len(research.context) if research.context else 0,
    )
    payload = _invoke_quiz_chain(
        source_text=source_text,
        topic_name=topic_name,
        question_count=question_count,
        research_context=research.context,
        used_knowledge_base=research.used_knowledge_base,
        should_cancel=should_cancel,
    )
    _raise_if_cancelled(should_cancel)
    logger.info(
        "quiz_generate=done mode=%s topic=%s questions=%s",
        research.mode,
        payload.topic_name,
        len(payload.questions),
    )
    return payload

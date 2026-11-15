"""Drill sampling, practice memory, status, lazy explanation."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import KbQuestion, KbQuestionPractice, KnowledgeBase
from app.exceptions import bad_request, not_found
from app.models.knowledge import DrillStatusPublic, KnowledgeBaseMode
from app.models.quiz import Question, QuestionType, QuizPayload
from app.services.knowledge_service import get_owned_base

logger = logging.getLogger(__name__)


def count_active_questions(db: Session, kb_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(KbQuestion)
            .where(
                KbQuestion.knowledge_base_id == kb_id,
                KbQuestion.is_active == 1,
            )
        )
        or 0
    )


def unseen_question_ids(db: Session, *, kb_id: int, user_id: int) -> list[int]:
    seen = select(KbQuestionPractice.question_id).where(
        KbQuestionPractice.user_id == user_id,
        KbQuestionPractice.knowledge_base_id == kb_id,
    )
    rows = db.scalars(
        select(KbQuestion.id)
        .where(
            KbQuestion.knowledge_base_id == kb_id,
            KbQuestion.is_active == 1,
            KbQuestion.id.not_in(seen),
        )
        .order_by(KbQuestion.id.asc())
    ).all()
    return list(rows)


def get_drill_status(
    db: Session,
    *,
    kb_id: int,
    user_id: int,
    auto_switched: bool = False,
) -> DrillStatusPublic:
    from app.db.models import KnowledgeDocument
    from app.models.knowledge import DocumentStatus
    from app.services.knowledge_service import count_kb_documents

    kb = get_owned_base(db, kb_id=kb_id, user_id=user_id)
    total = count_active_questions(db, kb_id)
    unseen = len(unseen_question_ids(db, kb_id=kb_id, user_id=user_id)) if total else 0
    mode = KnowledgeBaseMode(kb.mode) if kb.mode else None
    suggested = KnowledgeBaseMode(kb.suggested_mode) if kb.suggested_mode else None
    mode_confirmed = bool(kb.mode and kb.mode_confirmed_at)
    doc_count = count_kb_documents(db, kb_id)
    busy = bool(
        db.scalar(
            select(func.count())
            .select_from(KnowledgeDocument)
            .where(
                KnowledgeDocument.knowledge_base_id == kb_id,
                KnowledgeDocument.status.in_(
                    (
                        DocumentStatus.pending.value,
                        DocumentStatus.processing.value,
                        DocumentStatus.awaiting_mode.value,
                    )
                ),
            )
        )
    )
    # Only after there is a document and ingest has settled with zero usable questions.
    needs_empty = bool(
        mode == KnowledgeBaseMode.drill
        and mode_confirmed
        and total == 0
        and doc_count > 0
        and not busy
    )
    warning = None
    if auto_switched:
        warning = "因长时间未能拆出题目，已自动改为学透模式并重新入库"
        needs_empty = False
    elif needs_empty:
        warning = "未能识别题目，请更换规范题库文档，或改为学透模式"
    return DrillStatusPublic(
        knowledge_base_id=kb_id,
        mode=mode,
        suggested_mode=suggested,
        mode_confirmed=mode_confirmed,
        total_questions=total,
        unseen_questions=unseen,
        needs_review_prompt=bool(mode == KnowledgeBaseMode.drill and total > 0 and unseen == 0),
        needs_empty_drill_prompt=needs_empty,
        auto_switched_to_master=auto_switched,
        warning=warning,
    )


def reset_practice(db: Session, *, kb_id: int, user_id: int) -> None:
    get_owned_base(db, kb_id=kb_id, user_id=user_id)
    db.execute(
        delete(KbQuestionPractice).where(
            KbQuestionPractice.user_id == user_id,
            KbQuestionPractice.knowledge_base_id == kb_id,
        )
    )
    db.commit()


def sample_questions(
    db: Session,
    *,
    kb_id: int,
    user_id: int,
    n: int,
    review: bool = False,
) -> list[KbQuestion]:
    get_owned_base(db, kb_id=kb_id, user_id=user_id)
    if n < 1:
        raise bad_request("VALIDATION_ERROR", "题量至少为 1")
    active = db.scalars(
        select(KbQuestion).where(
            KbQuestion.knowledge_base_id == kb_id,
            KbQuestion.is_active == 1,
        )
    ).all()
    if not active:
        raise bad_request("DRILL_EMPTY", "刷题库没有可用题目")

    unseen_ids = set(unseen_question_ids(db, kb_id=kb_id, user_id=user_id))
    unseen = [q for q in active if q.id in unseen_ids]
    seen = [q for q in active if q.id not in unseen_ids]

    if not review:
        if not unseen and seen:
            raise bad_request(
                "DRILL_REVIEW_REQUIRED",
                "本库题目已全部刷过一遍，请选择复习轮或重置进度",
            )
        pool = unseen
    else:
        pool = seen or active

    random.shuffle(pool)
    picked = pool[: min(n, len(pool))]
    if not picked:
        raise bad_request("DRILL_EMPTY", "没有可抽题目")
    return picked


def question_to_payload_item(q: KbQuestion) -> Question:
    qtype = {
        "single": QuestionType.single,
        "multi": QuestionType.multiple,
        "judge": QuestionType.boolean,
    }.get(q.qtype, QuestionType.single)
    options = list(q.options_json or [])
    if qtype == QuestionType.boolean:
        options = ["正确", "错误"]
    explanation = q.explanation or ""
    if q.explanation_source == "ai" and explanation:
        explanation = f"【AI 解析】{explanation}"
    return Question(
        id=f"kbq-{q.id}",
        type=qtype,
        stem=q.stem,
        options=options,
        answer_indexes=list(q.answer_indices_json or []),
        explanation=explanation or "暂无解析",
    )


def assemble_quiz_payload(
    db: Session,
    *,
    kb: KnowledgeBase,
    user_id: int,
    question_count: int,
    review: bool = False,
) -> tuple[QuizPayload, list[KbQuestion]]:
    rows = sample_questions(
        db,
        kb_id=kb.id,
        user_id=user_id,
        n=question_count,
        review=review,
    )
    questions = [question_to_payload_item(q) for q in rows]
    return QuizPayload(topic_name=kb.name, questions=questions), rows


def mark_practiced(
    db: Session,
    *,
    user_id: int,
    kb_id: int,
    question_ids: list[int],
    correct_map: dict[int, bool] | None = None,
) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    correct_map = correct_map or {}
    for qid in question_ids:
        row = db.scalar(
            select(KbQuestionPractice).where(
                KbQuestionPractice.user_id == user_id,
                KbQuestionPractice.question_id == qid,
            )
        )
        if row is None:
            row = KbQuestionPractice(
                user_id=user_id,
                knowledge_base_id=kb_id,
                question_id=qid,
                last_seen_at=now,
                correct_count=0,
                wrong_count=0,
            )
            db.add(row)
        else:
            row.last_seen_at = now
        if qid in correct_map:
            if correct_map[qid]:
                row.correct_count += 1
            else:
                row.wrong_count += 1
    db.commit()


def ensure_mode_confirmed(kb: KnowledgeBase) -> None:
    if not kb.mode or not kb.mode_confirmed_at:
        raise bad_request("MODE_NOT_CONFIRMED", "请先确认知识库模式（刷题/学透）")


def get_question_owned(
    db: Session, *, kb_id: int, question_id: int, user_id: int
) -> KbQuestion:
    get_owned_base(db, kb_id=kb_id, user_id=user_id)
    row = db.get(KbQuestion, question_id)
    if row is None or row.knowledge_base_id != kb_id or not row.is_active:
        raise not_found("题目不存在")
    return row

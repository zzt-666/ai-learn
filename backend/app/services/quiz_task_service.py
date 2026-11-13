"""Async quiz generation tasks: enqueue, run in background, poll status."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.db import base as db_base
from app.db.models import QuizGenerationTask
from app.models.quiz import QuizPayload
from app.models.quiz_task import QuizTaskStatus, QuizTaskStatusResponse
from app.services.quiz_service import QuizTaskCancelled, generate_quiz
from app.services.tool_call_logging import preview_text

logger = logging.getLogger(__name__)

_CANCELABLE = frozenset(
    {
        QuizTaskStatus.pending.value,
        QuizTaskStatus.running.value,
    }
)


def create_generation_task(
    db: Session,
    *,
    user_id: int,
    source_text: str,
    topic_name: str | None,
    question_count: int,
) -> QuizGenerationTask:
    row = QuizGenerationTask(
        user_id=user_id,
        source_text=source_text,
        topic_name_input=topic_name,
        question_count=question_count,
        status=QuizTaskStatus.pending.value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info(
        "quiz_task=created id=%s user_id=%s n=%s clue=%s",
        row.id,
        user_id,
        question_count,
        preview_text(source_text, limit=80),
    )
    return row


def get_task_for_user(
    db: Session, *, task_id: int, user_id: int
) -> QuizGenerationTask | None:
    # Always hit DB so poll sees background worker commits.
    db.expire_all()
    row = db.get(QuizGenerationTask, task_id)
    if row is None or row.user_id != user_id:
        return None
    return row


def cancel_generation_task(
    db: Session, *, task_id: int, user_id: int
) -> QuizGenerationTask | None:
    """Mark pending/running task cancelled. Terminal statuses are left unchanged."""
    row = get_task_for_user(db, task_id=task_id, user_id=user_id)
    if row is None:
        return None
    if row.status in _CANCELABLE:
        row.status = QuizTaskStatus.cancelled.value
        row.error_message = "用户取消出题"
        row.finished_at = datetime.now()
        db.commit()
        db.refresh(row)
        logger.info("quiz_task=cancelled id=%s user_id=%s", task_id, user_id)
    else:
        logger.info(
            "quiz_task=cancel_noop id=%s status=%s",
            task_id,
            row.status,
        )
    return row


def to_status_response(row: QuizGenerationTask) -> QuizTaskStatusResponse:
    topic_name = None
    questions = None
    if row.status == QuizTaskStatus.succeeded.value and row.result_json:
        try:
            payload = QuizPayload.model_validate(row.result_json)
            topic_name = payload.topic_name
            questions = payload.questions
        except Exception:  # noqa: BLE001
            logger.exception("quiz_task=bad_result id=%s", row.id)

    return QuizTaskStatusResponse(
        task_id=row.id,
        status=QuizTaskStatus(row.status),
        topic_name=topic_name,
        questions=questions,
        error_message=row.error_message,
        created_at=row.created_at,
        finished_at=row.finished_at,
    )


def _task_is_cancelled(task_id: int) -> bool:
    """Fresh short session so MySQL RR / long worker sessions still see cancel."""
    check = db_base.SessionLocal()
    try:
        row = check.get(QuizGenerationTask, task_id)
        return row is None or row.status == QuizTaskStatus.cancelled.value
    finally:
        check.close()


def run_quiz_generation_task(task_id: int) -> None:
    """Background worker: owns its own DB session."""
    db = db_base.SessionLocal()
    try:
        row = db.get(QuizGenerationTask, task_id)
        if row is None:
            logger.warning("quiz_task=missing id=%s", task_id)
            return
        if row.status == QuizTaskStatus.cancelled.value:
            logger.info("quiz_task=skip_cancelled id=%s", task_id)
            return
        if row.status not in _CANCELABLE:
            logger.info("quiz_task=skip id=%s status=%s", task_id, row.status)
            return

        row.status = QuizTaskStatus.running.value
        db.commit()
        logger.info("quiz_task=running id=%s", task_id)

        if _task_is_cancelled(task_id):
            logger.info("quiz_task=aborted_before_generate id=%s", task_id)
            return

        source_text = row.source_text
        topic_name_input = row.topic_name_input
        question_count = row.question_count

        try:
            payload = generate_quiz(
                source_text=source_text,
                topic_name=topic_name_input,
                question_count=question_count,
                should_cancel=lambda: _task_is_cancelled(task_id),
            )
        except QuizTaskCancelled:
            logger.info("quiz_task=aborted_cooperative id=%s", task_id)
            db.expire_all()
            row = db.get(QuizGenerationTask, task_id)
            if row is not None and row.status != QuizTaskStatus.cancelled.value:
                row.status = QuizTaskStatus.cancelled.value
                row.error_message = "用户取消出题"
                row.finished_at = datetime.now()
                db.commit()
            return

        # User may have cancelled while the last LLM call finished.
        if _task_is_cancelled(task_id):
            logger.info("quiz_task=discard_after_cancel id=%s", task_id)
            return

        # End worker RR snapshot before deciding whether we may persist success.
        db.rollback()
        row = db.get(QuizGenerationTask, task_id)
        if row is None:
            return
        if row.status not in _CANCELABLE:
            logger.info(
                "quiz_task=discard_terminal id=%s status=%s",
                task_id,
                row.status,
            )
            return

        row.status = QuizTaskStatus.succeeded.value
        row.result_json = payload.model_dump(mode="json")
        row.error_message = None
        row.finished_at = datetime.now()
        db.commit()
        logger.info(
            "quiz_task=succeeded id=%s topic=%s questions=%s",
            task_id,
            payload.topic_name,
            len(payload.questions),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("quiz_task=failed id=%s err=%s", task_id, type(exc).__name__)
        try:
            db.expire_all()
            row = db.get(QuizGenerationTask, task_id)
            if row is None:
                return
            if row.status == QuizTaskStatus.cancelled.value:
                return
            row.status = QuizTaskStatus.failed.value
            row.error_message = (str(exc) or type(exc).__name__)[:500]
            row.finished_at = datetime.now()
            db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("quiz_task=fail_persist_error id=%s", task_id)
    finally:
        db.close()

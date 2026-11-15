"""Background worker: generate report for a completed quiz session."""

from __future__ import annotations

import logging

import app.db.base as db_base
from app.db.models import QuizSession
from app.models.quiz import Question, UserAnswer
from app.services.session_progress import (
    STATUS_COMPLETED,
    _ensure_report,
    _normalize_answers,
)

logger = logging.getLogger(__name__)


def run_session_report_task(session_id: int) -> None:
    """Owns its own DB session; no-op if report already present."""
    db = db_base.SessionLocal()
    try:
        row = db.get(QuizSession, session_id)
        if row is None:
            logger.warning("session_report=missing id=%s", session_id)
            return
        if row.status != STATUS_COMPLETED:
            logger.info(
                "session_report=skip id=%s status=%s", session_id, row.status
            )
            return
        if row.report_json:
            logger.info("session_report=already_ready id=%s", session_id)
            return

        questions = [Question.model_validate(q) for q in row.questions_json]
        raw_answers = [a for a in (row.answers_json or []) if a is not None]
        answers = [UserAnswer.model_validate(a) for a in raw_answers]
        normalized, correct_count, wrong_count, accuracy = _normalize_answers(
            questions, answers, require_complete=True
        )
        report = _ensure_report(
            topic_name=row.topic_name,
            source_text=row.source_text,
            questions=questions,
            answers=normalized,
            accuracy=accuracy,
            correct_count=correct_count,
            wrong_count=wrong_count,
            existing=None,
        )
        row.report_json = report.model_dump(mode="json")
        db.add(row)
        db.commit()
        logger.info("session_report=ready id=%s", session_id)
    except Exception:  # noqa: BLE001
        logger.exception("session_report=failed id=%s", session_id)
        db.rollback()
    finally:
        db.close()

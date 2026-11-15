from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import QuizSession, User
from app.exceptions import bad_request, not_found
from app.models.quiz import Question
from app.models.report import ReportPayload
from app.models.session import (
    HistoryDetail,
    HistoryItem,
    HistoryReportResponse,
    RetrySessionResponse,
)
from app.services.session_progress import STATUS_COMPLETED, STATUS_IN_PROGRESS
from app.services.shuffle import shuffle_questions


def _answered_count(row: QuizSession) -> int:
    answers = row.answers_json or []
    return sum(1 for a in answers if a is not None)


def _to_history_item(row: QuizSession) -> HistoryItem:
    return HistoryItem(
        id=row.id,
        topic_name=row.topic_name,
        finished_at=row.finished_at,
        updated_at=row.updated_at,
        accuracy=float(row.accuracy or 0.0),
        question_count=row.question_count,
        answered_count=_answered_count(row),
        exp_gained=int(row.exp_gained or 0),
        points_gained=int(row.points_gained or 0),
        status=row.status or STATUS_COMPLETED,
    )


def list_history(
    db: Session,
    *,
    user: User,
    limit: int = 50,
    status: str | None = None,
) -> list[HistoryItem]:
    stmt = select(QuizSession).where(QuizSession.user_id == user.id)
    if status:
        if status not in (STATUS_IN_PROGRESS, STATUS_COMPLETED):
            raise bad_request("INVALID_STATUS", "status 仅支持 in_progress 或 completed")
        stmt = stmt.where(QuizSession.status == status)
    rows = db.scalars(
        stmt.order_by(QuizSession.updated_at.desc()).limit(limit)
    ).all()
    return [_to_history_item(row) for row in rows]


def get_owned_session(db: Session, *, user: User, session_id: int) -> QuizSession:
    row = db.get(QuizSession, session_id)
    if row is None or row.user_id != user.id:
        raise not_found("闯关记录不存在")
    return row


def get_history_detail(db: Session, *, user: User, session_id: int) -> HistoryDetail:
    row = get_owned_session(db, user=user, session_id=session_id)
    return HistoryDetail(
        id=row.id,
        topic_name=row.topic_name,
        finished_at=row.finished_at,
        updated_at=row.updated_at,
        accuracy=float(row.accuracy or 0.0),
        correct_count=int(row.correct_count or 0),
        wrong_count=int(row.wrong_count or 0),
        question_count=row.question_count,
        answered_count=_answered_count(row),
        exp_gained=int(row.exp_gained or 0),
        points_gained=int(row.points_gained or 0),
        status=row.status or STATUS_COMPLETED,
        source_session_id=row.source_session_id,
        current_index=row.current_index or 0,
    )


def get_history_report(
    db: Session, *, user: User, session_id: int
) -> HistoryReportResponse:
    # Async report worker commits in another connection. End the current
    # transaction so MySQL REPEATABLE READ can see the latest row.
    db.commit()
    row = get_owned_session(db, user=user, session_id=session_id)
    if row.status != STATUS_COMPLETED:
        raise bad_request("NOT_COMPLETED", "未完成闯关暂无报告")
    if not row.report_json:
        return HistoryReportResponse(status="pending", report=None)
    return HistoryReportResponse(
        status="ready",
        report=ReportPayload.model_validate(row.report_json),
    )


def retry_session(db: Session, *, user: User, session_id: int) -> RetrySessionResponse:
    row = get_owned_session(db, user=user, session_id=session_id)
    if row.status != STATUS_COMPLETED:
        raise bad_request("NOT_COMPLETED", "未完成闯关不可重闯，请先继续答题")
    questions = [Question.model_validate(q) for q in row.questions_json]
    shuffled = shuffle_questions(questions)
    return RetrySessionResponse(
        topic_name=row.topic_name,
        source_text=row.source_text,
        questions=shuffled,
        source_session_id=row.id,
    )

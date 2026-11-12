from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import QuizSession, User
from app.exceptions import not_found
from app.models.quiz import Question
from app.models.report import ReportPayload
from app.models.session import HistoryDetail, HistoryItem, RetrySessionResponse
from app.services.shuffle import shuffle_questions


def list_history(db: Session, *, user: User, limit: int = 50) -> list[HistoryItem]:
    rows = db.scalars(
        select(QuizSession)
        .where(QuizSession.user_id == user.id)
        .order_by(QuizSession.finished_at.desc())
        .limit(limit)
    ).all()
    return [
        HistoryItem(
            id=row.id,
            topic_name=row.topic_name,
            finished_at=row.finished_at,
            accuracy=float(row.accuracy),
            exp_gained=row.exp_gained,
            points_gained=row.points_gained,
            status="completed",
        )
        for row in rows
    ]


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
        accuracy=float(row.accuracy),
        correct_count=row.correct_count,
        wrong_count=row.wrong_count,
        question_count=row.question_count,
        exp_gained=row.exp_gained,
        points_gained=row.points_gained,
        status="completed",
        source_session_id=row.source_session_id,
    )


def get_history_report(db: Session, *, user: User, session_id: int) -> ReportPayload:
    row = get_owned_session(db, user=user, session_id=session_id)
    return ReportPayload.model_validate(row.report_json)


def retry_session(db: Session, *, user: User, session_id: int) -> RetrySessionResponse:
    row = get_owned_session(db, user=user, session_id=session_id)
    questions = [Question.model_validate(q) for q in row.questions_json]
    shuffled = shuffle_questions(questions)
    return RetrySessionResponse(
        topic_name=row.topic_name,
        source_text=row.source_text,
        questions=shuffled,
        source_session_id=row.id,
    )

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import QuizSession, User
from app.exceptions import bad_request, not_found
from app.models.quiz import Question, UserAnswer
from app.models.report import ReportGenerateRequest, ReportItem, ReportPayload
from app.models.session import (
    CompleteSessionRequest,
    CompleteSessionResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    SessionDetail,
    UpdateProgressRequest,
)
from app.services.grading import is_correct
from app.services.report_service import generate_report
from app.services.rewards import calc_session_rewards
from app.services.users import apply_rewards, to_user_public

STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"


def _answered_count(answers_json: list | None) -> int:
    if not answers_json:
        return 0
    return sum(1 for a in answers_json if a is not None)


def _normalize_answers(
    questions: list[Question],
    answers: list[UserAnswer],
    *,
    require_complete: bool,
) -> tuple[list[dict], int, int, float]:
    q_by_id = {q.id: q for q in questions}
    if len(q_by_id) != len(questions):
        raise bad_request("INVALID_SESSION", "题目 id 重复")

    answer_ids = [a.question_id for a in answers]
    if len(answer_ids) != len(set(answer_ids)):
        raise bad_request("INVALID_SESSION", "作答 id 重复")
    unknown = set(answer_ids) - set(q_by_id.keys())
    if unknown:
        raise bad_request("INVALID_SESSION", "作答与题目不匹配")
    if require_complete and set(answer_ids) != set(q_by_id.keys()):
        raise bad_request("INVALID_SESSION", "作答与题目不匹配")

    correct_count = 0
    normalized: list[dict] = []
    for ans in answers:
        question = q_by_id[ans.question_id]
        ok = is_correct(question.answer_indexes, ans.selected_indexes)
        if ok:
            correct_count += 1
        normalized.append(
            {
                "question_id": ans.question_id,
                "selected_indexes": list(ans.selected_indexes),
                "is_correct": ok,
            }
        )

    total = len(questions)
    if require_complete:
        wrong_count = total - correct_count
        accuracy = (correct_count / total) if total else 0.0
    else:
        wrong_count = len(normalized) - correct_count
        accuracy = (correct_count / len(normalized)) if normalized else 0.0
    return normalized, correct_count, wrong_count, accuracy


def _get_owned(db: Session, *, user: User, session_id: int) -> QuizSession:
    row = db.get(QuizSession, session_id)
    if row is None or row.user_id != user.id:
        raise not_found("闯关记录不存在")
    return row


def _to_detail(row: QuizSession) -> SessionDetail:
    answers = [UserAnswer.model_validate(a) for a in (row.answers_json or []) if a is not None]
    report = None
    if row.report_json:
        report = ReportPayload.model_validate(row.report_json)
    return SessionDetail(
        id=row.id,
        topic_name=row.topic_name,
        source_text=row.source_text,
        questions=[Question.model_validate(q) for q in row.questions_json],
        answers=answers,
        current_index=row.current_index or 0,
        question_count=row.question_count,
        answered_count=_answered_count(row.answers_json),
        status=row.status,
        knowledge_base_id=row.knowledge_base_id,
        source_session_id=row.source_session_id,
        report=report,
        exp_gained=row.exp_gained,
        points_gained=row.points_gained,
        finished_at=row.finished_at,
        updated_at=row.updated_at,
    )


def _build_report_items(questions: list[Question], answers: list[dict]) -> list[ReportItem]:
    by_id = {a["question_id"]: a for a in answers}
    items: list[ReportItem] = []
    for q in questions:
        a = by_id.get(q.id, {})
        items.append(
            ReportItem(
                question_id=q.id,
                type=q.type,
                stem=q.stem,
                options=q.options,
                answer_indexes=q.answer_indexes,
                selected_indexes=list(a.get("selected_indexes") or []),
                is_correct=bool(a.get("is_correct")),
                explanation=q.explanation,
            )
        )
    return items


def _placeholder_report(
    *,
    accuracy: float,
    correct_count: int,
    wrong_count: int,
) -> ReportPayload:
    return ReportPayload(
        summary_points=["报告生成失败，可稍后在历史记录中重试生成"],
        accuracy=accuracy,
        correct_count=correct_count,
        wrong_count=wrong_count,
        wrong_review=[],
        weaknesses=["报告暂不可用"],
    )


def _ensure_report(
    *,
    topic_name: str,
    source_text: str,
    questions: list[Question],
    answers: list[dict],
    accuracy: float,
    correct_count: int,
    wrong_count: int,
    existing: ReportPayload | None,
) -> ReportPayload:
    if existing is not None:
        return existing.model_copy(
            update={
                "accuracy": accuracy,
                "correct_count": correct_count,
                "wrong_count": wrong_count,
            }
        )
    items = _build_report_items(questions, answers)
    try:
        return generate_report(
            ReportGenerateRequest(
                topic_name=topic_name,
                source_text_excerpt=source_text[:2000],
                correct_count=correct_count,
                wrong_count=wrong_count,
                accuracy=accuracy,
                items=items,
            )
        )
    except Exception:  # noqa: BLE001
        return _placeholder_report(
            accuracy=accuracy,
            correct_count=correct_count,
            wrong_count=wrong_count,
        )


def create_session(
    db: Session,
    *,
    user: User,
    body: CreateSessionRequest,
) -> CreateSessionResponse:
    if body.current_index >= len(body.questions):
        raise bad_request("INVALID_SESSION", "current_index 超出题目范围")
    if body.source_session_id is not None:
        src = db.get(QuizSession, body.source_session_id)
        if src is None or src.user_id != user.id:
            raise not_found("来源闯关不存在")

    normalized: list[dict] = []
    if body.answers:
        normalized, _, _, _ = _normalize_answers(
            body.questions, body.answers, require_complete=False
        )

    now = datetime.now()
    row = QuizSession(
        user_id=user.id,
        topic_name=body.topic_name.strip()[:64],
        source_text=body.source_text,
        question_count=len(body.questions),
        correct_count=None,
        wrong_count=None,
        accuracy=None,
        exp_gained=None,
        points_gained=None,
        questions_json=[q.model_dump(mode="json") for q in body.questions],
        answers_json=normalized,
        report_json=None,
        source_session_id=body.source_session_id,
        knowledge_base_id=body.knowledge_base_id,
        status=STATUS_IN_PROGRESS,
        current_index=body.current_index,
        finished_at=None,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return CreateSessionResponse(session_id=row.id, status=row.status)


def update_progress(
    db: Session,
    *,
    user: User,
    session_id: int,
    body: UpdateProgressRequest,
) -> SessionDetail:
    row = _get_owned(db, user=user, session_id=session_id)
    if row.status != STATUS_IN_PROGRESS:
        raise bad_request("INVALID_SESSION", "已通关会话不可更新进度")
    if body.current_index >= row.question_count:
        raise bad_request("INVALID_SESSION", "current_index 超出题目范围")

    questions = [Question.model_validate(q) for q in row.questions_json]
    normalized, _, _, _ = _normalize_answers(
        questions, body.answers, require_complete=False
    )
    if len(normalized) > row.question_count:
        raise bad_request("INVALID_SESSION", "作答数量超出题目数")

    row.answers_json = normalized
    row.current_index = body.current_index
    row.updated_at = datetime.now()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_detail(row)


def get_session(db: Session, *, user: User, session_id: int) -> SessionDetail:
    row = _get_owned(db, user=user, session_id=session_id)
    return _to_detail(row)


def _settle_completed_row(
    db: Session,
    *,
    user: User,
    row: QuizSession,
    questions: list[Question],
    normalized_answers: list[dict],
    correct_count: int,
    wrong_count: int,
    accuracy: float,
    report: ReportPayload | None,
    source_session_id: int | None,
) -> CompleteSessionResponse:
    if row.status == STATUS_COMPLETED:
        return CompleteSessionResponse(
            session_id=row.id,
            exp_gained=int(row.exp_gained or 0),
            points_gained=int(row.points_gained or 0),
            user=to_user_public(user),
        )

    exp_gained, points_gained = calc_session_rewards(
        correct_count=correct_count,
        total_count=len(questions),
    )
    apply_rewards(user, exp_gained=exp_gained, points_gained=points_gained)
    now = datetime.now()
    row.question_count = len(questions)
    row.correct_count = correct_count
    row.wrong_count = wrong_count
    row.accuracy = round(accuracy, 4)
    row.exp_gained = exp_gained
    row.points_gained = points_gained
    row.questions_json = [q.model_dump(mode="json") for q in questions]
    row.answers_json = normalized_answers
    row.report_json = report.model_dump(mode="json") if report is not None else None
    if source_session_id is not None:
        row.source_session_id = source_session_id
    row.status = STATUS_COMPLETED
    row.current_index = max(len(questions) - 1, 0)
    row.finished_at = now
    row.updated_at = now
    db.add(user)
    db.add(row)
    db.commit()
    db.refresh(user)
    db.refresh(row)
    return CompleteSessionResponse(
        session_id=row.id,
        exp_gained=exp_gained,
        points_gained=points_gained,
        user=to_user_public(user),
    )


def finish_session(
    db: Session,
    *,
    user: User,
    session_id: int,
) -> tuple[CompleteSessionResponse, bool]:
    """Silent complete: settle rewards immediately; report may be generated async.

    Returns (response, needs_async_report).
    """
    row = _get_owned(db, user=user, session_id=session_id)
    if row.status == STATUS_COMPLETED:
        return (
            CompleteSessionResponse(
                session_id=row.id,
                exp_gained=int(row.exp_gained or 0),
                points_gained=int(row.points_gained or 0),
                user=to_user_public(user),
            ),
            row.report_json is None,
        )

    questions = [Question.model_validate(q) for q in row.questions_json]
    raw_answers = [a for a in (row.answers_json or []) if a is not None]
    if len(raw_answers) != len(questions):
        raise bad_request("INVALID_SESSION", "尚未答完全部题目，无法通关")

    answers = [UserAnswer.model_validate(a) for a in raw_answers]
    normalized, correct_count, wrong_count, accuracy = _normalize_answers(
        questions, answers, require_complete=True
    )
    # Keep existing report if already present; otherwise leave null for async job.
    report = (
        ReportPayload.model_validate(row.report_json) if row.report_json else None
    )
    result = _settle_completed_row(
        db,
        user=user,
        row=row,
        questions=questions,
        normalized_answers=normalized,
        correct_count=correct_count,
        wrong_count=wrong_count,
        accuracy=accuracy,
        report=report,
        source_session_id=row.source_session_id,
    )
    return result, report is None


def complete_session(
    db: Session,
    *,
    user: User,
    body: CompleteSessionRequest,
) -> CompleteSessionResponse:
    normalized, correct_count, wrong_count, accuracy = _normalize_answers(
        body.questions, body.answers, require_complete=True
    )

    if body.source_session_id is not None:
        src = db.get(QuizSession, body.source_session_id)
        if src is None or src.user_id != user.id:
            raise not_found("来源闯关不存在")

    report = _ensure_report(
        topic_name=body.topic_name.strip()[:64],
        source_text=body.source_text,
        questions=body.questions,
        answers=normalized,
        accuracy=accuracy,
        correct_count=correct_count,
        wrong_count=wrong_count,
        existing=body.report,
    )

    if body.session_id is not None:
        row = _get_owned(db, user=user, session_id=body.session_id)
        row.topic_name = body.topic_name.strip()[:64]
        row.source_text = body.source_text
        return _settle_completed_row(
            db,
            user=user,
            row=row,
            questions=body.questions,
            normalized_answers=normalized,
            correct_count=correct_count,
            wrong_count=wrong_count,
            accuracy=accuracy,
            report=report,
            source_session_id=body.source_session_id,
        )

    # Legacy path: create a fresh completed row (no prior in_progress session).
    exp_gained, points_gained = calc_session_rewards(
        correct_count=correct_count,
        total_count=len(body.questions),
    )
    apply_rewards(user, exp_gained=exp_gained, points_gained=points_gained)
    now = datetime.now()
    session = QuizSession(
        user_id=user.id,
        topic_name=body.topic_name.strip()[:64],
        source_text=body.source_text,
        question_count=len(body.questions),
        correct_count=correct_count,
        wrong_count=wrong_count,
        accuracy=round(accuracy, 4),
        exp_gained=exp_gained,
        points_gained=points_gained,
        questions_json=[q.model_dump(mode="json") for q in body.questions],
        answers_json=normalized,
        report_json=report.model_dump(mode="json"),
        source_session_id=body.source_session_id,
        knowledge_base_id=None,
        status=STATUS_COMPLETED,
        current_index=max(len(body.questions) - 1, 0),
        finished_at=now,
        updated_at=now,
    )
    db.add(user)
    db.add(session)
    db.commit()
    db.refresh(user)
    db.refresh(session)
    return CompleteSessionResponse(
        session_id=session.id,
        exp_gained=exp_gained,
        points_gained=points_gained,
        user=to_user_public(user),
    )

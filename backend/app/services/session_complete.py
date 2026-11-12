from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import QuizSession, User
from app.exceptions import bad_request, not_found
from app.models.session import CompleteSessionRequest, CompleteSessionResponse
from app.services.grading import is_correct
from app.services.rewards import calc_session_rewards
from app.services.users import apply_rewards, to_user_public


def complete_session(
    db: Session,
    *,
    user: User,
    body: CompleteSessionRequest,
) -> CompleteSessionResponse:
    q_by_id = {q.id: q for q in body.questions}
    if len(q_by_id) != len(body.questions):
        raise bad_request("INVALID_SESSION", "题目 id 重复")

    answer_ids = [a.question_id for a in body.answers]
    if len(answer_ids) != len(set(answer_ids)):
        raise bad_request("INVALID_SESSION", "作答 id 重复")
    if set(answer_ids) != set(q_by_id.keys()):
        raise bad_request("INVALID_SESSION", "作答与题目不匹配")

    correct_count = 0
    normalized_answers = []
    for ans in body.answers:
        question = q_by_id[ans.question_id]
        ok = is_correct(question.answer_indexes, ans.selected_indexes)
        if ok:
            correct_count += 1
        normalized_answers.append(
            {
                "question_id": ans.question_id,
                "selected_indexes": list(ans.selected_indexes),
                "is_correct": ok,
            }
        )

    total = len(body.questions)
    wrong_count = total - correct_count
    accuracy = (correct_count / total) if total else 0.0
    exp_gained, points_gained = calc_session_rewards(
        correct_count=correct_count,
        total_count=total,
    )

    report = body.report.model_copy(
        update={
            "accuracy": accuracy,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
        }
    )

    if body.source_session_id is not None:
        src = db.get(QuizSession, body.source_session_id)
        if src is None or src.user_id != user.id:
            raise not_found("来源闯关不存在")

    apply_rewards(user, exp_gained=exp_gained, points_gained=points_gained)
    now = datetime.now()
    session = QuizSession(
        user_id=user.id,
        topic_name=body.topic_name.strip()[:64],
        source_text=body.source_text,
        question_count=total,
        correct_count=correct_count,
        wrong_count=wrong_count,
        accuracy=round(accuracy, 4),
        exp_gained=exp_gained,
        points_gained=points_gained,
        questions_json=[q.model_dump(mode="json") for q in body.questions],
        answers_json=normalized_answers,
        report_json=report.model_dump(mode="json"),
        source_session_id=body.source_session_id,
        finished_at=now,
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

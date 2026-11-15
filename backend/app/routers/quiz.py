import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import User
from app.deps import get_current_user
from app.exceptions import not_found
from app.models.errors import ErrorResponse
from app.models.quiz import QuizGenerateRequest, QuizPayload
from app.models.quiz_task import (
    QuizTaskCreateRequest,
    QuizTaskCreatedResponse,
    QuizTaskStatus,
    QuizTaskStatusResponse,
)
from app.services.knowledge_service import assert_kb_ready_for_quiz
from app.services.quiz_research import KnowledgeBaseGroundingError
from app.services.quiz_service import generate_quiz
from app.services.quiz_task_service import (
    cancel_generation_task,
    create_generation_task,
    get_task_for_user,
    run_quiz_generation_task,
    to_status_response,
)
from app.services.tool_call_logging import preview_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


def _prepare_kb_if_needed(
    db: Session, *, user_id: int, knowledge_base_id: int | None
) -> None:
    if knowledge_base_id is not None:
        assert_kb_ready_for_quiz(db, kb_id=knowledge_base_id, user_id=user_id)


@router.post(
    "/quiz/tasks",
    response_model=QuizTaskCreatedResponse,
    responses={401: {"model": ErrorResponse}},
)
def create_quiz_task(
    body: QuizTaskCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enqueue async quiz generation; returns immediately for client polling."""
    logger.info(
        "api quiz/tasks create user_id=%s n=%s kb_id=%s clue=%s",
        current_user.id,
        body.question_count,
        body.knowledge_base_id,
        preview_text(body.source_text, limit=80),
    )
    _prepare_kb_if_needed(
        db, user_id=current_user.id, knowledge_base_id=body.knowledge_base_id
    )
    row = create_generation_task(
        db,
        user_id=current_user.id,
        source_text=body.source_text,
        topic_name=body.topic_name,
        question_count=body.question_count,
        knowledge_base_id=body.knowledge_base_id,
        drill_round=body.drill_round,
    )
    background_tasks.add_task(run_quiz_generation_task, row.id)
    return QuizTaskCreatedResponse(
        task_id=row.id,
        status=QuizTaskStatus.pending,
    )


@router.get(
    "/quiz/tasks/{task_id}",
    response_model=QuizTaskStatusResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_quiz_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = get_task_for_user(db, task_id=task_id, user_id=current_user.id)
    if row is None:
        raise not_found("出题任务不存在")
    return to_status_response(row)


@router.post(
    "/quiz/tasks/{task_id}/cancel",
    response_model=QuizTaskStatusResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def cancel_quiz_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Abandon pending/running generation; worker stops at the next cancel checkpoint."""
    logger.info(
        "api quiz/tasks cancel user_id=%s task_id=%s",
        current_user.id,
        task_id,
    )
    row = cancel_generation_task(db, task_id=task_id, user_id=current_user.id)
    if row is None:
        raise not_found("出题任务不存在")
    return to_status_response(row)


@router.post(
    "/quiz/generate",
    response_model=QuizPayload,
    responses={401: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def create_quiz(
    body: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync generate (compat / tests). Prefer POST /quiz/tasks + poll in the mini program."""
    logger.info(
        "api quiz/generate user_id=%s n=%s kb_id=%s clue=%s",
        current_user.id,
        body.question_count,
        body.knowledge_base_id,
        preview_text(body.source_text, limit=80),
    )
    try:
        _prepare_kb_if_needed(
            db, user_id=current_user.id, knowledge_base_id=body.knowledge_base_id
        )
        return generate_quiz(
            source_text=body.source_text,
            topic_name=body.topic_name,
            question_count=body.question_count,
            db=db,
            user_id=current_user.id,
            knowledge_base_id=body.knowledge_base_id,
            drill_round=body.drill_round,
        )
    except KnowledgeBaseGroundingError as exc:
        logger.info("api quiz/generate kb_failed err=%s", exc)
        return JSONResponse(
            status_code=502,
            content={
                "error_code": "KB_GROUNDING_FAILED",
                "message": str(exc) or "知识库材料不足，无法出题",
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("api quiz/generate failed err=%s", type(exc).__name__)
        return JSONResponse(
            status_code=502,
            content={
                "error_code": "GENERATE_FAILED",
                "message": f"出题失败，请稍后重试（{exc}）"
                if str(exc)
                else "出题失败，请稍后重试",
            },
        )

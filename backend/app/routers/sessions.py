from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import User
from app.deps import get_current_user
from app.models.errors import ErrorResponse
from app.models.session import (
    CompleteSessionRequest,
    CompleteSessionResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    SessionDetail,
    UpdateProgressRequest,
)
from app.services import session_progress
from app.services.session_report_task import run_session_report_task

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=CreateSessionResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def create(
    body: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return session_progress.create_session(db, user=current_user, body=body)


@router.post(
    "/complete",
    response_model=CompleteSessionResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def complete(
    body: CompleteSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return session_progress.complete_session(db, user=current_user, body=body)


@router.patch(
    "/{session_id}/progress",
    response_model=SessionDetail,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def progress(
    session_id: int,
    body: UpdateProgressRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return session_progress.update_progress(
        db, user=current_user, session_id=session_id, body=body
    )


@router.post(
    "/{session_id}/finish",
    response_model=CompleteSessionResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def finish(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result, needs_report = session_progress.finish_session(
        db, user=current_user, session_id=session_id
    )
    if needs_report:
        background_tasks.add_task(run_session_report_task, result.session_id)
    return result


@router.get(
    "/{session_id}",
    response_model=SessionDetail,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_one(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return session_progress.get_session(db, user=current_user, session_id=session_id)

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import User
from app.deps import get_current_user
from app.models.errors import ErrorResponse
from app.models.report import ReportPayload
from app.models.session import HistoryDetail, HistoryItem, RetrySessionResponse
from app.services import history_service

router = APIRouter(prefix="/api/v1/history", tags=["history"])


@router.get(
    "",
    response_model=list[HistoryItem],
    responses={401: {"model": ErrorResponse}},
)
def list_history(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return history_service.list_history(db, user=current_user, limit=limit)


@router.get(
    "/{session_id}",
    response_model=HistoryDetail,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def history_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return history_service.get_history_detail(db, user=current_user, session_id=session_id)


@router.get(
    "/{session_id}/report",
    response_model=ReportPayload,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def history_report(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return history_service.get_history_report(db, user=current_user, session_id=session_id)


@router.post(
    "/{session_id}/retry",
    response_model=RetrySessionResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def history_retry(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return history_service.retry_session(db, user=current_user, session_id=session_id)

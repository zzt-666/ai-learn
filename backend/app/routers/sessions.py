from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import User
from app.deps import get_current_user
from app.models.errors import ErrorResponse
from app.models.session import CompleteSessionRequest, CompleteSessionResponse
from app.services.session_complete import complete_session

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


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
    return complete_session(db, user=current_user, body=body)

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.db.models import User
from app.deps import get_current_user
from app.models.errors import ErrorResponse
from app.models.quiz import QuizGenerateRequest, QuizPayload
from app.services.quiz_service import generate_quiz

router = APIRouter(prefix="/api/v1")


@router.post(
    "/quiz/generate",
    response_model=QuizPayload,
    responses={401: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def create_quiz(
    body: QuizGenerateRequest,
    _current_user: User = Depends(get_current_user),
):
    try:
        return generate_quiz(
            source_text=body.source_text,
            topic_name=body.topic_name,
            question_count=body.question_count,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=502,
            content={
                "error_code": "GENERATE_FAILED",
                "message": f"出题失败，请稍后重试（{exc}）"
                if str(exc)
                else "出题失败，请稍后重试",
            },
        )

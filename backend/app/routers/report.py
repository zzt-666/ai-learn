from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.db.models import User
from app.deps import get_current_user
from app.models.errors import ErrorResponse
from app.models.report import ReportGenerateRequest, ReportPayload
from app.services.report_service import generate_report

router = APIRouter(prefix="/api/v1")


@router.post(
    "/report/generate",
    response_model=ReportPayload,
    responses={401: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def create_report(
    body: ReportGenerateRequest,
    _current_user: User = Depends(get_current_user),
):
    try:
        return generate_report(body)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=502,
            content={
                "error_code": "REPORT_FAILED",
                "message": f"报告生成失败，请稍后重试（{exc}）"
                if str(exc)
                else "报告生成失败，请稍后重试",
            },
        )

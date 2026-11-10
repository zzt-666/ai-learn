from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.errors import ErrorResponse
from app.models.report import ReportGenerateRequest, ReportPayload
from app.services.report_service import generate_report

router = APIRouter(prefix="/api/v1")


@router.post(
    "/report/generate",
    response_model=ReportPayload,
    responses={502: {"model": ErrorResponse}},
)
def create_report(body: ReportGenerateRequest):
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

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(message)


def unauthorized(message: str = "请先登录") -> AppError:
    return AppError(401, "UNAUTHORIZED", message)


def not_found(message: str = "资源不存在") -> AppError:
    return AppError(404, "NOT_FOUND", message)


def bad_request(error_code: str, message: str) -> AppError:
    return AppError(400, error_code, message)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message},
    )

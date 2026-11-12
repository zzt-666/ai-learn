from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.base import get_db
from app.exceptions import AppError
from app.models.errors import ErrorResponse
from app.models.user import LoginResponse, WechatLoginRequest
from app.services.jwt_tokens import create_access_token
from app.services.users import get_or_create_user_by_openid, to_user_public
from app.services.wechat_auth import WechatAuthError, code_to_openid

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/wechat/login",
    response_model=LoginResponse,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def wechat_login(body: WechatLoginRequest, db: Session = Depends(get_db)):
    try:
        openid, unionid = code_to_openid(body.code)
    except WechatAuthError as exc:
        raise AppError(502, "LOGIN_FAILED", exc.message) from exc

    user = get_or_create_user_by_openid(db, openid=openid, unionid=unionid)
    settings = get_settings()
    token = create_access_token(user_id=user.id)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expire_days * 24 * 3600,
        user=to_user_public(user),
    )


@router.post("/logout")
def logout():
    """客户端清凭证即可；服务端无状态，占位成功。"""
    return {"ok": True}

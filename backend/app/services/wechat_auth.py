from __future__ import annotations

import httpx

from app.config import get_settings


class WechatAuthError(Exception):
    def __init__(self, message: str = "微信登录失败，请重试") -> None:
        self.message = message
        super().__init__(message)


def code_to_openid(code: str) -> tuple[str, str | None]:
    """用 code 换 openid（及可选 unionid）。返回 (openid, unionid)。"""
    code = (code or "").strip()
    if not code:
        raise WechatAuthError("登录凭证无效")

    settings = get_settings()
    if settings.wechat_mock_login:
        return f"mock_{code}", None

    if not settings.wechat_app_id or not settings.wechat_app_secret:
        raise WechatAuthError("微信登录配置缺失")

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.wechat_app_id,
        "secret": settings.wechat_app_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise WechatAuthError(f"微信接口异常：{exc}") from exc

    if "errcode" in data and data["errcode"] != 0:
        raise WechatAuthError(data.get("errmsg") or "微信登录失败，请重试")

    openid = data.get("openid")
    if not openid:
        raise WechatAuthError("微信未返回用户标识")
    return openid, data.get("unionid")

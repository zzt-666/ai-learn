from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError

from app.config import get_settings

ALGORITHM = "HS256"


def create_access_token(*, user_id: int, expire_seconds: int | None = None) -> str:
    settings = get_settings()
    if expire_seconds is not None:
        expire = datetime.now(timezone.utc) + timedelta(seconds=expire_seconds)
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except InvalidTokenError as exc:
        raise ValueError("invalid token") from exc

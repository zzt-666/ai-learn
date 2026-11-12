from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import User
from app.exceptions import unauthorized
from app.services.jwt_tokens import decode_access_token
from app.services.users import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise unauthorized()
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (ValueError, KeyError, TypeError):
        raise unauthorized("登录已失效，请重新登录") from None

    user = get_user_by_id(db, user_id)
    if user is None:
        raise unauthorized("登录已失效，请重新登录")
    return user

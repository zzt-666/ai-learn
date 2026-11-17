from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import User
from app.deps import get_current_user
from app.exceptions import bad_request
from app.models.errors import ErrorResponse
from app.models.user import UpdateProfileRequest, UserPublic
from app.services.object_storage import (
    avatar_key_from_url,
    get_object_storage,
)
from app.services.users import to_user_public

router = APIRouter(prefix="/api/v1", tags=["me"])
logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024


@router.get("/me", response_model=UserPublic, responses={401: {"model": ErrorResponse}})
def read_me(current_user: User = Depends(get_current_user)):
    return to_user_public(current_user)


@router.patch(
    "/me",
    response_model=UserPublic,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
)
def update_me(
    body: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.nickname is None:
        raise bad_request("INVALID_PROFILE", "没有可更新的字段")
    current_user.nickname = body.nickname
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return to_user_public(current_user)


@router.post(
    "/me/avatar",
    response_model=UserPublic,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise bad_request("INVALID_AVATAR", "仅支持 JPG / PNG / WEBP / GIF 头像")

    data = await file.read()
    if not data:
        raise bad_request("INVALID_AVATAR", "头像文件为空")
    if len(data) > MAX_AVATAR_BYTES:
        raise bad_request("INVALID_AVATAR", "头像不能超过 2MB")

    ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(content_type, ".jpg")
    key = f"avatars/{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    storage = get_object_storage()
    try:
        storage.put(key, data, content_type=content_type)
    except Exception as exc:  # noqa: BLE001
        logger.exception("avatar put failed key=%s", key)
        raise bad_request("STORAGE_ERROR", "头像存储失败，请稍后重试") from exc

    old_key = avatar_key_from_url(current_user.avatar_url)
    current_user.avatar_url = storage.public_url(key)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    if old_key and old_key != key:
        try:
            storage.delete(old_key)
        except Exception:  # noqa: BLE001
            logger.warning("failed to delete previous avatar key=%s", old_key, exc_info=True)

    return to_user_public(current_user)

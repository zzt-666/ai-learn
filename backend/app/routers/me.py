from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.base import get_db
from app.db.models import User
from app.deps import get_current_user
from app.exceptions import bad_request
from app.models.errors import ErrorResponse
from app.models.user import UpdateProfileRequest, UserPublic
from app.services.users import to_user_public

router = APIRouter(prefix="/api/v1", tags=["me"])

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

    settings = get_settings()
    avatar_dir = Path(settings.upload_dir) / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)

    ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(content_type, ".jpg")
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    path = avatar_dir / filename
    path.write_bytes(data)

    current_user.avatar_url = f"/uploads/avatars/{filename}"
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return to_user_public(current_user)

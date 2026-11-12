from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class UserPublic(BaseModel):
    id: int
    nickname: str
    avatar_url: str | None = None
    exp: int
    points: int
    level: int
    completed_count: int
    exp_to_next_level: int
    level_progress: float


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class UpdateProfileRequest(BaseModel):
    nickname: str | None = None

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("昵称不能为空")
        if len(cleaned) > 32:
            raise ValueError("昵称最多 32 个字")
        return cleaned

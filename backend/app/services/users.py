from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.models.user import UserPublic
from app.services.rewards import calc_level, calc_level_progress


DEFAULT_NICKNAME = "阿衰同学"


def to_user_public(user: User) -> UserPublic:
    progress, to_next = calc_level_progress(user.exp)
    return UserPublic(
        id=user.id,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        exp=user.exp,
        points=user.points,
        level=user.level,
        completed_count=user.completed_count,
        exp_to_next_level=to_next,
        level_progress=progress,
    )


def get_or_create_user_by_openid(
    db: Session,
    *,
    openid: str,
    unionid: str | None = None,
) -> User:
    user = db.scalar(select(User).where(User.openid == openid))
    if user:
        if unionid and not user.unionid:
            user.unionid = unionid
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    user = User(
        openid=openid,
        unionid=unionid,
        nickname=DEFAULT_NICKNAME,
        avatar_url=None,
        exp=0,
        points=0,
        level=1,
        completed_count=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def apply_rewards(user: User, *, exp_gained: int, points_gained: int) -> User:
    user.exp += exp_gained
    user.points += points_gained
    user.level = calc_level(user.exp)
    user.completed_count += 1
    return user

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    unionid: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    nickname: Mapped[str] = mapped_column(String(32), nullable=False, default="阿衰同学")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    exp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    sessions: Mapped[list["QuizSession"]] = relationship(back_populates="user")


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    topic_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False)
    accuracy: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=False)
    exp_gained: Mapped[int] = mapped_column(Integer, nullable=False)
    points_gained: Mapped[int] = mapped_column(Integer, nullable=False)
    questions_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    answers_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    report_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    source_session_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="sessions")

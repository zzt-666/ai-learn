from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
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
    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(back_populates="user")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    mode: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    suggested_mode: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    mode_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    empty_drill_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    master_map_status: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    master_map_error: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    master_point_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, index=True
    )

    user: Mapped["User"] = relationship(back_populates="knowledge_bases")
    documents: Mapped[list["KnowledgeDocument"]] = relationship(
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
    )
    questions: Mapped[list["KbQuestion"]] = relationship(
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
    )
    master_sections: Mapped[list["KbMasterSection"]] = relationship(
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
    )


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="documents")
    questions: Mapped[list["KbQuestion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class KbQuestion(Base):
    __tablename__ = "kb_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_documents.id"), nullable=False, index=True
    )
    qtype: Mapped[str] = mapped_column(String(16), nullable=False)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    answer_indices_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation_source: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="questions")
    document: Mapped["KnowledgeDocument"] = relationship(back_populates="questions")
    practices: Mapped[list["KbQuestionPractice"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )


class KbQuestionPractice(Base):
    __tablename__ = "kb_question_practice"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_kb_practice_user_question"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("kb_questions.id"), nullable=False, index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    question: Mapped["KbQuestion"] = relationship(back_populates="practices")


class KbMasterSection(Base):
    __tablename__ = "kb_master_sections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_documents.id"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_span: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="master_sections")
    points: Mapped[list["KbMasterPoint"]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
    )


class KbMasterPoint(Base):
    __tablename__ = "kb_master_points"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("kb_master_sections.id"), nullable=False, index=True
    )
    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    keywords_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    section: Mapped["KbMasterSection"] = relationship(back_populates="points")
    coverages: Mapped[list["KbMasterPointCoverage"]] = relationship(
        back_populates="point",
        cascade="all, delete-orphan",
    )


class KbMasterPointCoverage(Base):
    __tablename__ = "kb_master_point_coverage"
    __table_args__ = (
        UniqueConstraint("user_id", "point_id", name="uq_kb_master_coverage_user_point"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    point_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("kb_master_points.id"), nullable=False, index=True
    )
    seen_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    point: Mapped["KbMasterPoint"] = relationship(back_populates="coverages")


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


class QuizGenerationTask(Base):
    """Async quiz generation job (create → poll → succeed/fail)."""

    __tablename__ = "quiz_generation_tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    topic_name_input: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    knowledge_base_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("knowledge_bases.id"), nullable=True, index=True
    )
    drill_round: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    result_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

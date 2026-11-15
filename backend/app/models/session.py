from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.quiz import Question, UserAnswer
from app.models.report import ReportPayload
from app.models.user import UserPublic


class CreateSessionRequest(BaseModel):
    topic_name: str = Field(min_length=1, max_length=64)
    source_text: str = Field(min_length=1)
    questions: list[Question] = Field(min_length=1)
    answers: list[UserAnswer] = Field(default_factory=list)
    current_index: int = Field(default=0, ge=0)
    knowledge_base_id: int | None = None
    source_session_id: int | None = None


class CreateSessionResponse(BaseModel):
    session_id: int
    status: str = "in_progress"


class UpdateProgressRequest(BaseModel):
    answers: list[UserAnswer] = Field(default_factory=list)
    current_index: int = Field(ge=0)


class SessionDetail(BaseModel):
    id: int
    topic_name: str
    source_text: str
    questions: list[Question]
    answers: list[UserAnswer]
    current_index: int
    question_count: int
    answered_count: int
    status: str
    knowledge_base_id: int | None = None
    source_session_id: int | None = None
    report: ReportPayload | None = None
    exp_gained: int | None = None
    points_gained: int | None = None
    finished_at: datetime | None = None
    updated_at: datetime | None = None


class CompleteSessionRequest(BaseModel):
    topic_name: str = Field(min_length=1, max_length=64)
    source_text: str = Field(min_length=1)
    questions: list[Question] = Field(min_length=1)
    answers: list[UserAnswer] = Field(min_length=1)
    report: ReportPayload | None = None
    source_session_id: int | None = None
    session_id: int | None = None


class CompleteSessionResponse(BaseModel):
    session_id: int
    exp_gained: int
    points_gained: int
    user: UserPublic


class HistoryItem(BaseModel):
    id: int
    topic_name: str
    finished_at: datetime | None = None
    updated_at: datetime | None = None
    accuracy: float = 0.0
    question_count: int
    answered_count: int = 0
    exp_gained: int = 0
    points_gained: int = 0
    status: str = "completed"


class HistoryDetail(BaseModel):
    id: int
    topic_name: str
    finished_at: datetime | None = None
    updated_at: datetime | None = None
    accuracy: float = 0.0
    correct_count: int = 0
    wrong_count: int = 0
    question_count: int
    answered_count: int = 0
    exp_gained: int = 0
    points_gained: int = 0
    status: str = "completed"
    source_session_id: int | None = None
    current_index: int = 0


class RetrySessionResponse(BaseModel):
    topic_name: str
    source_text: str
    questions: list[Question]
    source_session_id: int


class HistoryReportResponse(BaseModel):
    status: Literal["ready", "pending"]
    report: ReportPayload | None = None

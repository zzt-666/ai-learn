from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.quiz import Question, UserAnswer
from app.models.report import ReportPayload
from app.models.user import UserPublic


class CompleteSessionRequest(BaseModel):
    topic_name: str = Field(min_length=1, max_length=64)
    source_text: str = Field(min_length=1)
    questions: list[Question] = Field(min_length=1)
    answers: list[UserAnswer] = Field(min_length=1)
    report: ReportPayload
    source_session_id: int | None = None


class CompleteSessionResponse(BaseModel):
    session_id: int
    exp_gained: int
    points_gained: int
    user: UserPublic


class HistoryItem(BaseModel):
    id: int
    topic_name: str
    finished_at: datetime
    accuracy: float
    question_count: int
    exp_gained: int
    points_gained: int
    status: str = "completed"


class HistoryDetail(BaseModel):
    id: int
    topic_name: str
    finished_at: datetime
    accuracy: float
    correct_count: int
    wrong_count: int
    question_count: int
    exp_gained: int
    points_gained: int
    status: str = "completed"
    source_session_id: int | None = None


class RetrySessionResponse(BaseModel):
    topic_name: str
    source_text: str
    questions: list[Question]
    source_session_id: int

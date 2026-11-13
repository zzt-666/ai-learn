from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from app.models.quiz import Question, QuizGenerateRequest


class QuizTaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class QuizTaskCreateRequest(QuizGenerateRequest):
    """Same body as sync generate; creates an async task instead."""


class QuizTaskCreatedResponse(BaseModel):
    task_id: int
    status: QuizTaskStatus


class QuizTaskStatusResponse(BaseModel):
    task_id: int
    status: QuizTaskStatus
    topic_name: str | None = None
    questions: list[Question] | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    finished_at: datetime | None = None

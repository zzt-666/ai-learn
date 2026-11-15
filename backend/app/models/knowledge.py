from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class DocumentStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    awaiting_mode = "awaiting_mode"
    ready = "ready"
    failed = "failed"


class KnowledgeBaseMode(str, Enum):
    drill = "drill"
    master = "master"


class MasterMapStatus(str, Enum):
    pending = "pending"
    ready = "ready"
    failed = "failed"


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=256)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("name must not be empty")
        return text

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=256)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("name must not be empty")
        return text


class KnowledgeBaseConfirmMode(BaseModel):
    mode: KnowledgeBaseMode
    """Allow switching even after mode was locked (default True for re-confirm)."""
    force: bool = True


class KnowledgeBasePublic(BaseModel):
    id: int
    name: str
    description: str | None
    mode: KnowledgeBaseMode | None = None
    suggested_mode: KnowledgeBaseMode | None = None
    mode_confirmed_at: datetime | None = None
    empty_drill_at: datetime | None = None
    ready_document_count: int = 0
    document_count: int = 0
    active_question_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KnowledgeDocumentPublic(BaseModel):
    id: int
    knowledge_base_id: int
    filename: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    error_message: str | None = None
    chunk_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DrillStatusPublic(BaseModel):
    knowledge_base_id: int
    mode: KnowledgeBaseMode | None
    suggested_mode: KnowledgeBaseMode | None
    mode_confirmed: bool
    total_questions: int
    unseen_questions: int
    needs_review_prompt: bool
    needs_empty_drill_prompt: bool = False
    auto_switched_to_master: bool = False
    warning: str | None = None


class MasterStatusPublic(BaseModel):
    knowledge_base_id: int
    map_status: MasterMapStatus | None = None
    total_points: int = 0
    covered_points: int = 0
    uncovered_points: int = 0
    needs_review_prompt: bool = False
    warning: str | None = None
    error_message: str | None = None

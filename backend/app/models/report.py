from pydantic import BaseModel, Field

from app.models.quiz import QuestionType


class ReportItem(BaseModel):
    question_id: str
    type: QuestionType
    stem: str
    options: list[str]
    answer_indexes: list[int]
    selected_indexes: list[int]
    is_correct: bool
    explanation: str


class ReportGenerateRequest(BaseModel):
    topic_name: str
    source_text_excerpt: str = ""
    correct_count: int = Field(ge=0)
    wrong_count: int = Field(ge=0)
    accuracy: float = Field(ge=0, le=1)
    items: list[ReportItem] = Field(min_length=1)


class WrongReviewItem(BaseModel):
    question_id: str
    type: QuestionType
    stem: str
    brief_reason: str


class ReportPayload(BaseModel):
    summary_points: list[str] = Field(min_length=1)
    accuracy: float
    correct_count: int
    wrong_count: int
    wrong_review: list[WrongReviewItem] = Field(default_factory=list)
    weaknesses: list[str] = Field(min_length=1)

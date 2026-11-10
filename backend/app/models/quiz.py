from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class QuestionType(str, Enum):
    single = "single"
    multiple = "multiple"
    boolean = "boolean"


class Question(BaseModel):
    id: str
    type: QuestionType
    stem: str
    options: list[str] = Field(min_length=2)
    answer_indexes: list[int] = Field(min_length=1)
    explanation: str

    @model_validator(mode="after")
    def validate_by_type(self):
        n = len(self.options)
        if any(i < 0 or i >= n for i in self.answer_indexes):
            raise ValueError("answer_indexes out of range")
        if self.type == QuestionType.boolean:
            if self.options != ["正确", "错误"] or len(self.answer_indexes) != 1:
                raise ValueError("boolean must be 正确/错误 with one answer")
        if self.type == QuestionType.single and len(self.answer_indexes) != 1:
            raise ValueError("single needs exactly one answer")
        if self.type == QuestionType.multiple and len(set(self.answer_indexes)) < 2:
            raise ValueError("multiple needs at least two distinct answers")
        return self


class QuizGenerateRequest(BaseModel):
    source_text: str
    topic_name: str | None = None
    question_count: int = Field(default=6, ge=5, le=10)

    @field_validator("source_text")
    @classmethod
    def strip_and_require_non_empty(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("source_text must not be empty")
        return text

    @field_validator("topic_name")
    @classmethod
    def normalize_topic_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class QuizPayload(BaseModel):
    topic_name: str
    questions: list[Question] = Field(min_length=1)

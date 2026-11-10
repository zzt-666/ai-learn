from langchain_core.prompts import ChatPromptTemplate

from app.models.quiz import QuizPayload
from app.services.llm import get_quiz_llm
from app.services.prompts import QUIZ_HUMAN, QUIZ_SYSTEM
from app.services.quiz_validate import validate_quiz_mix


def _build_quiz_chain():
    llm = get_quiz_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", QUIZ_SYSTEM),
            ("human", QUIZ_HUMAN),
        ]
    )
    return prompt | llm.with_structured_output(QuizPayload)


def generate_quiz(
    source_text: str,
    topic_name: str | None,
    question_count: int,
) -> QuizPayload:
    chain = _build_quiz_chain()
    inputs = {
        "source_text": source_text,
        "topic_name": topic_name or "",
        "question_count": question_count,
    }

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            result = chain.invoke(inputs)
            if not isinstance(result, QuizPayload):
                result = QuizPayload.model_validate(result)
            if topic_name:
                result.topic_name = topic_name
            validate_quiz_mix(result, expected_count=question_count)
            return result
        except Exception as exc:  # noqa: BLE001 - 业务层统一包装
            last_error = exc
            if attempt == 0:
                inputs = {
                    **inputs,
                    "topic_name": (topic_name or "") + "",
                    "source_text": source_text
                    + "\n\n（请严格遵守题型字段与题量，至少包含单选与判断；"
                    "围绕主题用你的已有知识出有区分度的题，禁止字面检索类弱题。）",
                }
                continue
            break

    raise RuntimeError(f"出题失败：{last_error}")

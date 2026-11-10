import json

from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings
from app.models.report import ReportGenerateRequest, ReportPayload
from app.services.grading import summarize_answers
from app.services.llm import get_report_llm
from app.services.prompts import REPORT_HUMAN, REPORT_SYSTEM


def _build_report_chain():
    llm = get_report_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", REPORT_SYSTEM),
            ("human", REPORT_HUMAN),
        ]
    )
    return prompt | llm.with_structured_output(ReportPayload)


def generate_report(request: ReportGenerateRequest) -> ReportPayload:
    settings = get_settings()
    summary = summarize_answers([item.model_dump() for item in request.items])
    correct_count = int(summary["correct_count"])
    wrong_count = int(summary["wrong_count"])
    accuracy = float(summary["accuracy"])

    excerpt = request.source_text_excerpt[: settings.source_excerpt_max_chars]
    items_json = json.dumps(
        [item.model_dump(mode="json") for item in request.items],
        ensure_ascii=False,
    )

    chain = _build_report_chain()
    inputs = {
        "topic_name": request.topic_name,
        "accuracy": accuracy,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "source_text_excerpt": excerpt,
        "items_json": items_json,
    }

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            result = chain.invoke(inputs)
            if not isinstance(result, ReportPayload):
                result = ReportPayload.model_validate(result)
            # 数值以服务端重算为准
            result.accuracy = accuracy
            result.correct_count = correct_count
            result.wrong_count = wrong_count
            if wrong_count == 0:
                result.wrong_review = []
            return result
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == 0:
                continue
            break

    raise RuntimeError(f"报告生成失败：{last_error}")

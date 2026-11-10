from unittest.mock import MagicMock, patch

from app.models.quiz import QuestionType
from app.models.report import ReportGenerateRequest, ReportItem, ReportPayload, WrongReviewItem
from app.services.report_service import generate_report


def test_generate_report_recomputes_stats():
    request = ReportGenerateRequest(
        topic_name="主题",
        source_text_excerpt="材料",
        correct_count=99,
        wrong_count=99,
        accuracy=0.99,
        items=[
            ReportItem(
                question_id="q1",
                type=QuestionType.single,
                stem="题1",
                options=["A", "B", "C"],
                answer_indexes=[0],
                selected_indexes=[0],
                is_correct=True,
                explanation="讲解",
            ),
            ReportItem(
                question_id="q2",
                type=QuestionType.boolean,
                stem="题2",
                options=["正确", "错误"],
                answer_indexes=[1],
                selected_indexes=[0],
                is_correct=False,
                explanation="讲解",
            ),
        ],
    )
    mocked = ReportPayload(
        summary_points=["要点"],
        accuracy=0.99,
        correct_count=99,
        wrong_count=99,
        wrong_review=[
            WrongReviewItem(
                question_id="q2",
                type=QuestionType.boolean,
                stem="题2",
                brief_reason="选错",
            )
        ],
        weaknesses=["巩固判断题"],
    )
    chain = MagicMock()
    chain.invoke.return_value = mocked

    with patch("app.services.report_service._build_report_chain", return_value=chain):
        result = generate_report(request)

    assert result.correct_count == 1
    assert result.wrong_count == 1
    assert result.accuracy == 0.5

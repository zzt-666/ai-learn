from app.models.report import ReportGenerateRequest, ReportItem, ReportPayload
from app.models.quiz import QuestionType


def test_report_payload_structure():
    report = ReportPayload(
        summary_points=["要点1", "要点2", "要点3"],
        accuracy=0.6667,
        correct_count=4,
        wrong_count=2,
        wrong_review=[
            {
                "question_id": "q1",
                "type": QuestionType.multiple,
                "stem": "原料题",
                "brief_reason": "漏选了水",
            }
        ],
        weaknesses=["原料产物易混"],
    )
    assert len(report.summary_points) == 3
    assert report.wrong_review[0].question_id == "q1"


def test_report_request_accepts_items():
    req = ReportGenerateRequest(
        topic_name="光合作用要点闯关",
        source_text_excerpt="叶绿体是光合作用的主要场所。",
        correct_count=1,
        wrong_count=1,
        accuracy=0.5,
        items=[
            ReportItem(
                question_id="q1",
                type=QuestionType.single,
                stem="场所？",
                options=["线粒体", "叶绿体", "液泡"],
                answer_indexes=[1],
                selected_indexes=[1],
                is_correct=True,
                explanation="叶绿体。",
            ),
            ReportItem(
                question_id="q2",
                type=QuestionType.boolean,
                stem="夜晚完全停止。",
                options=["正确", "错误"],
                answer_indexes=[1],
                selected_indexes=[0],
                is_correct=False,
                explanation="仍有呼吸。",
            ),
        ],
    )
    assert len(req.items) == 2

from unittest.mock import patch

from app.models.quiz import QuestionType
from app.models.report import ReportPayload, WrongReviewItem


def _mock_report() -> ReportPayload:
    return ReportPayload(
        summary_points=["场所在叶绿体", "原料是 CO2 与水", "别一刀切说夜晚停代谢"],
        accuracy=0.5,
        correct_count=1,
        wrong_count=1,
        wrong_review=[
            WrongReviewItem(
                question_id="q2",
                type=QuestionType.boolean,
                stem="夜晚完全停止。",
                brief_reason="忽略了呼吸等代谢",
            )
        ],
        weaknesses=["昼夜代谢容易拧"],
    )


def test_generate_report_success(client, auth_headers):
    payload = {
        "topic_name": "光合作用要点闯关",
        "source_text_excerpt": "叶绿体是光合作用的主要场所。",
        "correct_count": 1,
        "wrong_count": 1,
        "accuracy": 0.5,
        "items": [
            {
                "question_id": "q1",
                "type": "single",
                "stem": "场所？",
                "options": ["线粒体", "叶绿体", "液泡"],
                "answer_indexes": [1],
                "selected_indexes": [1],
                "is_correct": True,
                "explanation": "叶绿体。",
            },
            {
                "question_id": "q2",
                "type": "boolean",
                "stem": "夜晚完全停止。",
                "options": ["正确", "错误"],
                "answer_indexes": [1],
                "selected_indexes": [0],
                "is_correct": False,
                "explanation": "仍有呼吸。",
            },
        ],
    }
    with patch("app.routers.report.generate_report", return_value=_mock_report()):
        response = client.post(
            "/api/v1/report/generate",
            headers=auth_headers,
            json=payload,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["correct_count"] == 1
    assert data["wrong_count"] == 1
    assert len(data["summary_points"]) >= 1
    assert len(data["wrong_review"]) == 1


def test_generate_report_failed(client, auth_headers):
    payload = {
        "topic_name": "测试",
        "source_text_excerpt": "材料",
        "correct_count": 0,
        "wrong_count": 1,
        "accuracy": 0.0,
        "items": [
            {
                "question_id": "q1",
                "type": "single",
                "stem": "题",
                "options": ["A", "B", "C"],
                "answer_indexes": [0],
                "selected_indexes": [1],
                "is_correct": False,
                "explanation": "讲解",
            }
        ],
    }
    with patch(
        "app.routers.report.generate_report",
        side_effect=RuntimeError("报告失败"),
    ):
        response = client.post(
            "/api/v1/report/generate",
            headers=auth_headers,
            json=payload,
        )
    assert response.status_code == 502
    assert response.json()["error_code"] == "REPORT_FAILED"

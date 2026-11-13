from unittest.mock import MagicMock, patch

from app.models.quiz import Question, QuestionType, QuizPayload


def _mock_payload() -> QuizPayload:
    return QuizPayload(
        topic_name="光合作用要点闯关",
        questions=[
            Question(
                id="q1",
                type=QuestionType.single,
                stem="光合作用的主要场所是？",
                options=["线粒体", "叶绿体", "液泡", "核糖体"],
                answer_indexes=[1],
                explanation="材料写了叶绿体。",
            ),
            Question(
                id="q2",
                type=QuestionType.multiple,
                stem="下列哪些是光合作用的原料？（多选）",
                options=["二氧化碳", "水", "氧气", "葡萄糖"],
                answer_indexes=[0, 1],
                explanation="原料是二氧化碳与水。",
            ),
            Question(
                id="q3",
                type=QuestionType.boolean,
                stem="夜晚植物完全停止一切代谢。",
                options=["正确", "错误"],
                answer_indexes=[1],
                explanation="仍有呼吸等代谢。",
            ),
            Question(
                id="q4",
                type=QuestionType.single,
                stem="光反应主要发生在？",
                options=["细胞质", "类囊体膜", "细胞核", "液泡膜"],
                answer_indexes=[1],
                explanation="类囊体膜上进行光反应。",
            ),
            Question(
                id="q5",
                type=QuestionType.single,
                stem="下列哪项是产物？",
                options=["二氧化碳", "水", "氧气", "氮气"],
                answer_indexes=[2],
                explanation="氧气是产物。",
            ),
            Question(
                id="q6",
                type=QuestionType.boolean,
                stem="叶绿体是光合作用的主要场所。",
                options=["正确", "错误"],
                answer_indexes=[0],
                explanation="材料明确写出。",
            ),
        ],
    )


def test_generate_quiz_success(client, auth_headers):
    with patch("app.routers.quiz.generate_quiz", return_value=_mock_payload()) as mocked:
        response = client.post(
            "/api/v1/quiz/generate",
            headers=auth_headers,
            json={"source_text": "叶绿体是光合作用的主要场所。", "question_count": 6},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["topic_name"] == "光合作用要点闯关"
    assert len(data["questions"]) == 6
    mocked.assert_called_once()


def test_generate_quiz_empty_text(client, auth_headers):
    response = client.post(
        "/api/v1/quiz/generate",
        headers=auth_headers,
        json={"source_text": "  "},
    )
    assert response.status_code == 422


def test_generate_quiz_failed(client, auth_headers):
    with patch(
        "app.routers.quiz.generate_quiz",
        side_effect=RuntimeError("上游失败"),
    ):
        response = client.post(
            "/api/v1/quiz/generate",
            headers=auth_headers,
            json={"source_text": "光合作用材料"},
        )
    assert response.status_code == 502
    body = response.json()
    assert body["error_code"] == "GENERATE_FAILED"
    assert "message" in body


def test_generate_quiz_grounded_success_same_contract(client, auth_headers):
    """增强成功时响应形状与原先一致，无来源字段。"""
    with patch("app.routers.quiz.generate_quiz", return_value=_mock_payload()):
        response = client.post(
            "/api/v1/quiz/generate",
            headers=auth_headers,
            json={"source_text": "Harness Engineering", "question_count": 6},
        )
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"topic_name", "questions"}
    assert "sources" not in data
    assert "research_context" not in data


def test_generate_quiz_silent_degrade_same_error_shape(client, auth_headers):
    """检索失败静默降级后若模型出题仍失败，错误码仍为 GENERATE_FAILED。"""
    with patch(
        "app.routers.quiz.generate_quiz",
        side_effect=RuntimeError("出题失败：校验未通过"),
    ):
        response = client.post(
            "/api/v1/quiz/generate",
            headers=auth_headers,
            json={"source_text": "https://example.com/doc"},
        )
    assert response.status_code == 502
    body = response.json()
    assert body["error_code"] == "GENERATE_FAILED"
    assert "检索失败" not in body["message"]
    assert "已降级" not in body["message"]

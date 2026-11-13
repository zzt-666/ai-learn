from unittest.mock import patch

from app.models.quiz import Question, QuestionType, QuizPayload
from app.services.quiz_task_service import run_quiz_generation_task


def _mock_payload() -> QuizPayload:
    return QuizPayload(
        topic_name="异步出题主题",
        questions=[
            Question(
                id="q1",
                type=QuestionType.single,
                stem="单选1",
                options=["A", "B", "C", "D"],
                answer_indexes=[1],
                explanation="e",
            ),
            Question(
                id="q2",
                type=QuestionType.multiple,
                stem="多选1（多选）",
                options=["A", "B", "C", "D"],
                answer_indexes=[0, 2],
                explanation="e",
            ),
            Question(
                id="q3",
                type=QuestionType.boolean,
                stem="判断1",
                options=["正确", "错误"],
                answer_indexes=[0],
                explanation="e",
            ),
            Question(
                id="q4",
                type=QuestionType.single,
                stem="单选2",
                options=["A", "B", "C"],
                answer_indexes=[0],
                explanation="e",
            ),
            Question(
                id="q5",
                type=QuestionType.single,
                stem="单选3",
                options=["A", "B", "C"],
                answer_indexes=[2],
                explanation="e",
            ),
            Question(
                id="q6",
                type=QuestionType.boolean,
                stem="判断2",
                options=["正确", "错误"],
                answer_indexes=[1],
                explanation="e",
            ),
        ],
    )


def test_create_task_returns_immediately(client, auth_headers):
    with patch(
        "app.routers.quiz.run_quiz_generation_task",
        autospec=True,
    ) as runner:
        resp = client.post(
            "/api/v1/quiz/tasks",
            headers=auth_headers,
            json={"source_text": "Harness Engineering", "question_count": 6},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "task_id" in body
    assert body["status"] == "pending"
    runner.assert_called_once_with(body["task_id"])


def test_poll_task_succeeded(client, auth_headers, db_session):
    with patch("app.routers.quiz.run_quiz_generation_task", autospec=True):
        created = client.post(
            "/api/v1/quiz/tasks",
            headers=auth_headers,
            json={"source_text": "光合作用", "question_count": 6},
        ).json()

    task_id = created["task_id"]
    with patch(
        "app.services.quiz_task_service.generate_quiz",
        return_value=_mock_payload(),
    ):
        run_quiz_generation_task(task_id)

    # End this session's MySQL REPEATABLE READ snapshot so poll sees worker commits.
    db_session.rollback()
    poll = client.get(f"/api/v1/quiz/tasks/{task_id}", headers=auth_headers)
    assert poll.status_code == 200
    data = poll.json()
    assert data["status"] == "succeeded"
    assert data["topic_name"] == "异步出题主题"
    assert len(data["questions"]) == 6


def test_poll_task_failed(client, auth_headers, db_session):
    with patch("app.routers.quiz.run_quiz_generation_task", autospec=True):
        created = client.post(
            "/api/v1/quiz/tasks",
            headers=auth_headers,
            json={"source_text": "坏主题", "question_count": 6},
        ).json()
    task_id = created["task_id"]

    with patch(
        "app.services.quiz_task_service.generate_quiz",
        side_effect=RuntimeError("上游失败"),
    ):
        run_quiz_generation_task(task_id)

    db_session.rollback()
    poll = client.get(f"/api/v1/quiz/tasks/{task_id}", headers=auth_headers)
    assert poll.status_code == 200
    data = poll.json()
    assert data["status"] == "failed"
    assert data["questions"] is None
    assert "上游失败" in (data["error_message"] or "")


def test_poll_task_forbidden_other_user(client, auth_headers, other_auth_headers):
    with patch("app.routers.quiz.run_quiz_generation_task", autospec=True):
        created = client.post(
            "/api/v1/quiz/tasks",
            headers=auth_headers,
            json={"source_text": "私有任务", "question_count": 6},
        ).json()

    resp = client.get(
        f"/api/v1/quiz/tasks/{created['task_id']}",
        headers=other_auth_headers,
    )
    assert resp.status_code == 404


def test_cancel_pending_task(client, auth_headers, db_session):
    with patch("app.routers.quiz.run_quiz_generation_task", autospec=True):
        created = client.post(
            "/api/v1/quiz/tasks",
            headers=auth_headers,
            json={"source_text": "取消测试", "question_count": 6},
        ).json()
    task_id = created["task_id"]

    resp = client.post(
        f"/api/v1/quiz/tasks/{task_id}/cancel",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    db_session.rollback()
    poll = client.get(f"/api/v1/quiz/tasks/{task_id}", headers=auth_headers)
    assert poll.json()["status"] == "cancelled"


def test_cancel_stops_runner_before_persist(client, auth_headers, db_session):
    with patch("app.routers.quiz.run_quiz_generation_task", autospec=True):
        created = client.post(
            "/api/v1/quiz/tasks",
            headers=auth_headers,
            json={"source_text": "中断生成", "question_count": 6},
        ).json()
    task_id = created["task_id"]

    cancel = client.post(
        f"/api/v1/quiz/tasks/{task_id}/cancel",
        headers=auth_headers,
    )
    assert cancel.json()["status"] == "cancelled"

    with patch(
        "app.services.quiz_task_service.generate_quiz",
        return_value=_mock_payload(),
    ) as gen:
        run_quiz_generation_task(task_id)
        gen.assert_not_called()

    db_session.rollback()
    poll = client.get(f"/api/v1/quiz/tasks/{task_id}", headers=auth_headers)
    assert poll.json()["status"] == "cancelled"
    assert poll.json()["questions"] is None


def test_cancel_during_generate_discards_result(client, auth_headers, db_session):
    with patch("app.routers.quiz.run_quiz_generation_task", autospec=True):
        created = client.post(
            "/api/v1/quiz/tasks",
            headers=auth_headers,
            json={"source_text": "生成中取消", "question_count": 6},
        ).json()
    task_id = created["task_id"]

    def _fake_generate(*_args, **kwargs):
        should_cancel = kwargs.get("should_cancel")
        # Simulate user cancel while model would still be running.
        client.post(
            f"/api/v1/quiz/tasks/{task_id}/cancel",
            headers=auth_headers,
        )
        if should_cancel and should_cancel():
            from app.services.quiz_service import QuizTaskCancelled

            raise QuizTaskCancelled()
        return _mock_payload()

    with patch(
        "app.services.quiz_task_service.generate_quiz",
        side_effect=_fake_generate,
    ):
        run_quiz_generation_task(task_id)

    db_session.rollback()
    poll = client.get(f"/api/v1/quiz/tasks/{task_id}", headers=auth_headers)
    assert poll.json()["status"] == "cancelled"
    assert poll.json()["questions"] is None

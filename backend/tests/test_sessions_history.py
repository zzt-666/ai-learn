from copy import deepcopy
from unittest.mock import patch

from app.models.quiz import Question, QuestionType
from app.models.report import ReportPayload, WrongReviewItem


def _questions():
    return [
        Question(
            id="q1",
            type=QuestionType.single,
            stem="场所？",
            options=["线粒体", "叶绿体", "液泡"],
            answer_indexes=[1],
            explanation="叶绿体",
        ),
        Question(
            id="q2",
            type=QuestionType.boolean,
            stem="夜晚完全停止。",
            options=["正确", "错误"],
            answer_indexes=[1],
            explanation="仍有呼吸",
        ),
        Question(
            id="q3",
            type=QuestionType.multiple,
            stem="原料？（多选）",
            options=["二氧化碳", "水", "氧气"],
            answer_indexes=[0, 1],
            explanation="CO2和水",
        ),
    ]


def _mock_report() -> ReportPayload:
    return ReportPayload(
        summary_points=["要点1", "要点2"],
        accuracy=2 / 3,
        correct_count=2,
        wrong_count=1,
        wrong_review=[
            WrongReviewItem(
                question_id="q2",
                type=QuestionType.boolean,
                stem="夜晚完全停止。",
                brief_reason="忽略呼吸",
            )
        ],
        weaknesses=["昼夜代谢"],
    )


def _complete_payload(source_session_id=None, session_id=None):
    questions = _questions()
    answers = [
        {"question_id": "q1", "selected_indexes": [1], "is_correct": True},
        {"question_id": "q2", "selected_indexes": [0], "is_correct": False},
        {"question_id": "q3", "selected_indexes": [0, 1], "is_correct": True},
    ]
    report = _mock_report()
    payload = {
        "topic_name": "光合作用要点闯关",
        "source_text": "叶绿体是光合作用的主要场所。",
        "questions": [q.model_dump(mode="json") for q in questions],
        "answers": answers,
        "report": report.model_dump(mode="json"),
        "source_session_id": source_session_id,
    }
    if session_id is not None:
        payload["session_id"] = session_id
    return payload


def _create_payload(**overrides):
    questions = _questions()
    body = {
        "topic_name": "光合作用要点闯关",
        "source_text": "叶绿体是光合作用的主要场所。",
        "questions": [q.model_dump(mode="json") for q in questions],
        "answers": [],
        "current_index": 0,
    }
    body.update(overrides)
    return body


def test_complete_session_awards_and_lists(client, auth_headers):
    resp = client.post(
        "/api/v1/sessions/complete",
        headers=auth_headers,
        json=_complete_payload(),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # 对 2/3：EXP=2*20+1*5=45；积分=2*5=10
    assert data["exp_gained"] == 45
    assert data["points_gained"] == 10
    assert data["user"]["exp"] == 45
    assert data["user"]["points"] == 10
    assert data["user"]["completed_count"] == 1
    assert data["user"]["level"] == 1
    session_id = data["session_id"]

    hist = client.get("/api/v1/history", headers=auth_headers)
    assert hist.status_code == 200
    items = hist.json()
    assert len(items) == 1
    assert items[0]["id"] == session_id
    assert items[0]["status"] == "completed"
    assert items[0]["exp_gained"] == 45
    assert items[0]["question_count"] == 3
    assert items[0]["answered_count"] == 3

    detail = client.get(f"/api/v1/history/{session_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["topic_name"] == "光合作用要点闯关"

    report = client.get(f"/api/v1/history/{session_id}/report", headers=auth_headers)
    assert report.status_code == 200
    body = report.json()
    assert body["status"] == "ready"
    assert body["report"]["correct_count"] == 2


def test_history_forbidden_for_other_user(client, auth_headers, other_auth_headers):
    created = client.post(
        "/api/v1/sessions/complete",
        headers=auth_headers,
        json=_complete_payload(),
    ).json()
    sid = created["session_id"]

    resp = client.get(f"/api/v1/history/{sid}", headers=other_auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_retry_shuffles_question_order_not_options(client, auth_headers):
    created = client.post(
        "/api/v1/sessions/complete",
        headers=auth_headers,
        json=_complete_payload(),
    ).json()
    sid = created["session_id"]

    # 固定随机种子，保证可断言「顺序发生变化」的同时集合一致
    with patch("app.services.history_service.shuffle_questions") as mocked:
        qs = _questions()
        reordered = [qs[2], qs[0], qs[1]]
        mocked.return_value = reordered
        resp = client.post(f"/api/v1/history/{sid}/retry", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["source_session_id"] == sid
    assert [q["id"] for q in body["questions"]] == ["q3", "q1", "q2"]
    # 选项未打乱
    assert body["questions"][0]["options"] == ["二氧化碳", "水", "氧气"]
    assert body["questions"][0]["answer_indexes"] == [0, 1]


def test_retry_then_complete_keeps_old_session(client, auth_headers):
    first = client.post(
        "/api/v1/sessions/complete",
        headers=auth_headers,
        json=_complete_payload(),
    ).json()
    sid = first["session_id"]

    retry = client.post(f"/api/v1/history/{sid}/retry", headers=auth_headers).json()
    payload = _complete_payload(source_session_id=sid)
    payload["questions"] = retry["questions"]
    # 按新顺序重写 answers 对应
    payload["answers"] = [
        {
            "question_id": q["id"],
            "selected_indexes": deepcopy(
                next(a for a in _complete_payload()["answers"] if a["question_id"] == q["id"])
            )["selected_indexes"],
            "is_correct": True,
        }
        for q in retry["questions"]
    ]

    second = client.post(
        "/api/v1/sessions/complete",
        headers=auth_headers,
        json=payload,
    )
    assert second.status_code == 200, second.text
    assert second.json()["session_id"] != sid

    hist = client.get("/api/v1/history", headers=auth_headers).json()
    assert len(hist) == 2

    me = client.get("/api/v1/me", headers=auth_headers).json()
    assert me["completed_count"] == 2
    assert me["exp"] == first["user"]["exp"] + second.json()["exp_gained"]


def test_create_progress_resume_roundtrip(client, auth_headers, other_auth_headers):
    created = client.post(
        "/api/v1/sessions",
        headers=auth_headers,
        json=_create_payload(),
    )
    assert created.status_code == 200, created.text
    sid = created.json()["session_id"]
    assert created.json()["status"] == "in_progress"

    partial = [
        {"question_id": "q1", "selected_indexes": [1], "is_correct": True},
    ]
    patched = client.patch(
        f"/api/v1/sessions/{sid}/progress",
        headers=auth_headers,
        json={"answers": partial, "current_index": 1},
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["answered_count"] == 1
    assert body["current_index"] == 1
    assert body["status"] == "in_progress"
    assert body["answers"][0]["question_id"] == "q1"

    foreign = client.patch(
        f"/api/v1/sessions/{sid}/progress",
        headers=other_auth_headers,
        json={"answers": partial, "current_index": 1},
    )
    assert foreign.status_code == 404

    detail = client.get(f"/api/v1/sessions/{sid}", headers=auth_headers)
    assert detail.status_code == 200
    data = detail.json()
    assert data["id"] == sid
    assert len(data["questions"]) == 3
    assert data["answers"][0]["selected_indexes"] == [1]
    assert data["current_index"] == 1

    hist = client.get("/api/v1/history", headers=auth_headers).json()
    assert len(hist) == 1
    assert hist[0]["status"] == "in_progress"
    assert hist[0]["answered_count"] == 1
    assert hist[0]["question_count"] == 3

    report = client.get(f"/api/v1/history/{sid}/report", headers=auth_headers)
    assert report.status_code == 400
    assert report.json()["error_code"] == "NOT_COMPLETED"

    retry = client.post(f"/api/v1/history/{sid}/retry", headers=auth_headers)
    assert retry.status_code == 400


def test_silent_finish_idempotent_and_home_limit(client, auth_headers):
    # Create 4 unfinished sessions; home limit should return 3.
    sids = []
    for i in range(4):
        resp = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json=_create_payload(topic_name=f"主题{i}"),
        )
        assert resp.status_code == 200, resp.text
        sids.append(resp.json()["session_id"])

    home = client.get(
        "/api/v1/history?status=in_progress&limit=3",
        headers=auth_headers,
    )
    assert home.status_code == 200
    home_items = home.json()
    assert len(home_items) == 3
    assert all(item["status"] == "in_progress" for item in home_items)

    all_unfinished = client.get(
        "/api/v1/history?status=in_progress&limit=50",
        headers=auth_headers,
    ).json()
    assert len(all_unfinished) == 4

    # Fill answers on first session and silent-finish.
    sid = sids[0]
    answers = _complete_payload()["answers"]
    client.patch(
        f"/api/v1/sessions/{sid}/progress",
        headers=auth_headers,
        json={"answers": answers, "current_index": 2},
    )

    with patch("app.routers.sessions.run_session_report_task") as mocked_task:
        finished = client.post(f"/api/v1/sessions/{sid}/finish", headers=auth_headers)
        assert finished.status_code == 200, finished.text
        assert mocked_task.called
        first = finished.json()
        assert first["exp_gained"] == 45

        again = client.post(f"/api/v1/sessions/{sid}/finish", headers=auth_headers)
        assert again.status_code == 200
        assert again.json()["exp_gained"] == 45
        assert again.json()["user"]["exp"] == first["user"]["exp"]
        assert again.json()["user"]["completed_count"] == 1

    detail = client.get(f"/api/v1/sessions/{sid}", headers=auth_headers).json()
    assert detail["status"] == "completed"
    assert detail["report"] is None

    with patch("app.routers.history.run_session_report_task"):
        pending = client.get(f"/api/v1/history/{sid}/report", headers=auth_headers)
        assert pending.status_code == 200
        assert pending.json()["status"] == "pending"

    with patch(
        "app.services.session_report_task._ensure_report",
        return_value=_mock_report(),
    ):
        from app.services.session_report_task import run_session_report_task

        run_session_report_task(sid)

    report = client.get(f"/api/v1/history/{sid}/report", headers=auth_headers)
    assert report.status_code == 200
    assert report.json()["status"] == "ready"
    assert report.json()["report"]["correct_count"] == 2

    unfinished = client.get(
        "/api/v1/history?status=in_progress",
        headers=auth_headers,
    ).json()
    assert len(unfinished) == 3
    assert all(item["id"] != sid for item in unfinished)


def test_complete_with_session_id_settles_once(client, auth_headers):
    created = client.post(
        "/api/v1/sessions",
        headers=auth_headers,
        json=_create_payload(),
    ).json()
    sid = created["session_id"]
    payload = _complete_payload(session_id=sid)
    first = client.post(
        "/api/v1/sessions/complete",
        headers=auth_headers,
        json=payload,
    )
    assert first.status_code == 200, first.text
    second = client.post(
        "/api/v1/sessions/complete",
        headers=auth_headers,
        json=payload,
    )
    assert second.status_code == 200
    assert second.json()["session_id"] == sid
    assert second.json()["user"]["completed_count"] == 1
    assert second.json()["user"]["exp"] == first.json()["user"]["exp"]


def test_new_quiz_keeps_previous_unfinished(client, auth_headers):
    first = client.post(
        "/api/v1/sessions",
        headers=auth_headers,
        json=_create_payload(topic_name="旧局"),
    ).json()
    second = client.post(
        "/api/v1/sessions",
        headers=auth_headers,
        json=_create_payload(topic_name="新局"),
    ).json()
    assert first["session_id"] != second["session_id"]

    hist = client.get("/api/v1/history?status=in_progress", headers=auth_headers).json()
    assert len(hist) == 2
    ids = {item["id"] for item in hist}
    assert first["session_id"] in ids
    assert second["session_id"] in ids

    # Retry of completed creates a distinct new session via create after retry.
    done = client.post(
        "/api/v1/sessions/complete",
        headers=auth_headers,
        json=_complete_payload(),
    ).json()
    retry = client.post(
        f"/api/v1/history/{done['session_id']}/retry",
        headers=auth_headers,
    ).json()
    fresh = client.post(
        "/api/v1/sessions",
        headers=auth_headers,
        json=_create_payload(
            topic_name=retry["topic_name"],
            questions=retry["questions"],
            source_session_id=retry["source_session_id"],
        ),
    ).json()
    assert fresh["session_id"] != done["session_id"]

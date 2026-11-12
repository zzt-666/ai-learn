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


def _complete_payload(source_session_id=None):
    questions = _questions()
    answers = [
        {"question_id": "q1", "selected_indexes": [1], "is_correct": True},
        {"question_id": "q2", "selected_indexes": [0], "is_correct": False},
        {"question_id": "q3", "selected_indexes": [0, 1], "is_correct": True},
    ]
    report = ReportPayload(
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
    return {
        "topic_name": "光合作用要点闯关",
        "source_text": "叶绿体是光合作用的主要场所。",
        "questions": [q.model_dump(mode="json") for q in questions],
        "answers": answers,
        "report": report.model_dump(mode="json"),
        "source_session_id": source_session_id,
    }


def test_complete_session_awards_and_lists(client, auth_headers):
    resp = client.post(
        "/api/v1/sessions/complete",
        headers=auth_headers,
        json=_complete_payload(),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # 对 2/3：EXP=40+20=60；积分=round(2/3*40)=27
    assert data["exp_gained"] == 60
    assert data["points_gained"] == 27
    assert data["user"]["exp"] == 60
    assert data["user"]["points"] == 27
    assert data["user"]["completed_count"] == 1
    assert data["user"]["level"] == 1
    session_id = data["session_id"]

    hist = client.get("/api/v1/history", headers=auth_headers)
    assert hist.status_code == 200
    items = hist.json()
    assert len(items) == 1
    assert items[0]["id"] == session_id
    assert items[0]["status"] == "completed"
    assert items[0]["exp_gained"] == 60

    detail = client.get(f"/api/v1/history/{session_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["topic_name"] == "光合作用要点闯关"

    report = client.get(f"/api/v1/history/{session_id}/report", headers=auth_headers)
    assert report.status_code == 200
    assert report.json()["correct_count"] == 2


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

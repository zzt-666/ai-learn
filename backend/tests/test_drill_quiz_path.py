from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import KbQuestion, KnowledgeBase, KnowledgeDocument, User
from app.services import drill_explain, quiz_service
from app.services.drill_service import assemble_quiz_payload


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _user(db: Session) -> User:
    user = User(openid=f"dq_{uuid.uuid4().hex[:16]}", nickname="dq")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_drill(db: Session, user: User, *, with_questions: bool = True):
    kb = KnowledgeBase(
        user_id=user.id,
        name="path-test",
        mode="drill",
        mode_confirmed_at=_now(),
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    doc = KnowledgeDocument(
        knowledge_base_id=kb.id,
        user_id=user.id,
        filename="b.md",
        content_type="text/markdown",
        size_bytes=8,
        storage_path="x/b.md",
        status="ready",
        chunk_count=1,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    rows = []
    if with_questions:
        for i in range(2):
            q = KbQuestion(
                knowledge_base_id=kb.id,
                document_id=doc.id,
                qtype="single",
                stem=f"题{i+1}?",
                options_json=["A", "B"],
                answer_indices_json=[0],
                explanation="原文解析" if i == 0 else None,
                explanation_source="source" if i == 0 else "none",
                is_active=1,
            )
            db.add(q)
            rows.append(q)
        db.commit()
        for q in rows:
            db.refresh(q)
    return kb, doc, rows


def test_drill_generate_skips_research(db_session: Session, monkeypatch: pytest.MonkeyPatch):
    user = _user(db_session)
    kb, _doc, _rows = _seed_drill(db_session, user)

    def boom(*_a, **_k):
        raise AssertionError("gather_research_context must not run for drill")

    monkeypatch.setattr(quiz_service, "gather_research_context", boom)

    payload = quiz_service.generate_quiz(
        source_text="ignored",
        topic_name=None,
        question_count=2,
        db=db_session,
        user_id=user.id,
        knowledge_base_id=kb.id,
    )
    assert len(payload.questions) == 2
    assert payload.topic_name == kb.name


def test_drill_empty_blocks_api(client: TestClient, auth_headers: dict[str, str], db_session: Session):
    # Login user then seed empty drill kb owned by same openid user
    me = client.get("/api/v1/me", headers=auth_headers).json()
    user_id = me["id"]
    kb = KnowledgeBase(
        user_id=user_id,
        name="empty-drill",
        mode="drill",
        mode_confirmed_at=_now(),
    )
    db_session.add(kb)
    db_session.commit()
    db_session.refresh(kb)

    resp = client.post(
        "/api/v1/quiz/tasks",
        headers=auth_headers,
        json={
            "source_text": "x",
            "knowledge_base_id": kb.id,
            "question_count": 3,
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "DRILL_EMPTY"


def test_lazy_explanation_caches_ai(db_session: Session, monkeypatch: pytest.MonkeyPatch):
    user = _user(db_session)
    _kb, _doc, rows = _seed_drill(db_session, user)
    q = rows[1]
    assert q.explanation_source == "none"

    class FakeOut:
        explanation = "这是 AI 生成的解析。"

    chain = MagicMock()
    chain.invoke.return_value = FakeOut()

    class FakePrompt:
        def __or__(self, _other):
            return chain

    monkeypatch.setattr(
        drill_explain.ChatPromptTemplate,
        "from_messages",
        staticmethod(lambda *_a, **_k: FakePrompt()),
    )
    monkeypatch.setattr(
        drill_explain,
        "get_quiz_llm",
        lambda: MagicMock(with_structured_output=lambda _s: MagicMock()),
    )

    text1, src1 = drill_explain.ensure_ai_explanation(db_session, question=q)
    assert src1 == "ai"
    assert "解析" in text1
    assert chain.invoke.call_count == 1

    text2, src2 = drill_explain.ensure_ai_explanation(db_session, question=q)
    assert src2 == "ai"
    assert text2 == text1
    assert chain.invoke.call_count == 1  # cached, no second LLM call


def test_assemble_payload_maps_types(db_session: Session):
    user = _user(db_session)
    kb, _doc, rows = _seed_drill(db_session, user)
    payload, picked = assemble_quiz_payload(
        db_session, kb=kb, user_id=user.id, question_count=2
    )
    assert len(payload.questions) == len(picked) == 2
    assert all(q.id.startswith("kbq-") for q in payload.questions)

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import (
    KbMasterPoint,
    KbMasterPointCoverage,
    KbMasterSection,
    KnowledgeBase,
    KnowledgeDocument,
)
from app.models.quiz import Question, QuestionType, QuizPayload
from app.services import quiz_service


def _seed(db: Session, user_id: int, *, status: str = "ready", points: int = 3) -> KnowledgeBase:
    kb = KnowledgeBase(
        user_id=user_id,
        name="master-quiz",
        mode="master",
        mode_confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        master_map_status=status,
        master_point_count=points if status == "ready" else 0,
    )
    db.add(kb)
    db.flush()
    doc = KnowledgeDocument(
        knowledge_base_id=kb.id,
        user_id=user_id,
        filename="a.md",
        content_type="text/markdown",
        size_bytes=1,
        storage_path="a.md",
        status="ready",
        chunk_count=1,
    )
    db.add(doc)
    db.flush()
    if status == "ready" and points:
        sec = KbMasterSection(
            knowledge_base_id=kb.id,
            document_id=doc.id,
            ordinal=0,
            title="节",
        )
        db.add(sec)
        db.flush()
        for i in range(points):
            db.add(
                KbMasterPoint(
                    section_id=sec.id,
                    knowledge_base_id=kb.id,
                    ordinal=i,
                    title=f"P{i}",
                    summary=f"S{i}",
                    is_active=1,
                )
            )
    db.commit()
    db.refresh(kb)
    return kb


def _fake_payload() -> QuizPayload:
    return QuizPayload(
        topic_name="t",
        questions=[
            Question(
                id="1",
                type=QuestionType.single,
                stem="题干",
                options=["A", "B", "C", "D"],
                answer_indexes=[0],
                explanation="解析",
            )
        ],
    )


def test_master_ready_uses_points_path(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    monkeypatch,
):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    kb = _seed(db_session, me["id"], status="ready", points=3)

    seen_contexts: list[str] = []

    def _fake_invoke(**kwargs):
        seen_contexts.append(kwargs.get("research_context") or "")
        return _fake_payload()

    monkeypatch.setattr(quiz_service, "_invoke_quiz_chain", _fake_invoke)
    monkeypatch.setattr(
        "app.services.kb_tools.retrieve_kb_context",
        lambda **_k: "",
    )

    payload = quiz_service.generate_quiz(
        source_text="根据知识库出题",
        topic_name=None,
        question_count=4,
        db=db_session,
        user_id=me["id"],
        knowledge_base_id=kb.id,
    )
    assert payload.topic_name == "t"
    assert seen_contexts
    assert "要点" in seen_contexts[0] or "P0" in seen_contexts[0] or "S0" in seen_contexts[0]
    # Coverage written on start
    cov = (
        db_session.query(KbMasterPointCoverage)
        .filter_by(user_id=me["id"], knowledge_base_id=kb.id)
        .all()
    )
    assert len(cov) >= 2


def test_master_pending_degrades_to_legacy(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    monkeypatch,
):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    kb = _seed(db_session, me["id"], status="pending", points=0)

    called = {"gather": False}

    def _fake_gather(*_a, **_k):
        called["gather"] = True
        from app.services.quiz_research import ResearchResult

        return ResearchResult(context="legacy chunks", used_knowledge_base=True, mode="kb_forced")

    monkeypatch.setattr(quiz_service, "gather_research_context", _fake_gather)
    monkeypatch.setattr(quiz_service, "_invoke_quiz_chain", lambda **_k: _fake_payload())

    quiz_service.generate_quiz(
        source_text="根据知识库出题",
        topic_name=None,
        question_count=4,
        db=db_session,
        user_id=me["id"],
        knowledge_base_id=kb.id,
    )
    assert called["gather"] is True
    assert (
        db_session.query(KbMasterPointCoverage)
        .filter_by(knowledge_base_id=kb.id)
        .count()
        == 0
    )


def test_master_full_coverage_requires_review_flag(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    kb = _seed(db_session, me["id"], status="ready", points=2)
    points = db_session.query(KbMasterPoint).filter_by(knowledge_base_id=kb.id).all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for p in points:
        db_session.add(
            KbMasterPointCoverage(
                user_id=me["id"],
                knowledge_base_id=kb.id,
                point_id=p.id,
                seen_count=1,
                last_seen_at=now,
            )
        )
    db_session.commit()

    from app.exceptions import AppError

    try:
        quiz_service.generate_quiz(
            source_text="根据知识库出题",
            topic_name=None,
            question_count=4,
            db=db_session,
            user_id=me["id"],
            knowledge_base_id=kb.id,
        )
        raised = None
    except AppError as exc:
        raised = exc
    assert raised is not None
    assert raised.error_code == "MASTER_NEEDS_REVIEW"

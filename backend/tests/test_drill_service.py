from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.models import KbQuestion, KnowledgeBase, KnowledgeDocument, User
from app.exceptions import AppError
from app.services import drill_service


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _user(db: Session) -> User:
    user = User(openid=f"drill_{uuid.uuid4().hex[:16]}", nickname="drill")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed(db: Session, user: User) -> tuple[KnowledgeBase, KnowledgeDocument]:
    kb = KnowledgeBase(
        user_id=user.id,
        name="drill-test",
        mode="drill",
        mode_confirmed_at=_now(),
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    doc = KnowledgeDocument(
        knowledge_base_id=kb.id,
        user_id=user.id,
        filename="bank.md",
        content_type="text/markdown",
        size_bytes=10,
        storage_path="x/bank.md",
        status="ready",
        chunk_count=0,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return kb, doc


def _add_q(db: Session, kb: KnowledgeBase, doc: KnowledgeDocument, stem: str) -> KbQuestion:
    q = KbQuestion(
        knowledge_base_id=kb.id,
        document_id=doc.id,
        qtype="single",
        stem=stem,
        options_json=["A", "B"],
        answer_indices_json=[0],
        explanation="解析",
        explanation_source="source",
        is_active=1,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def test_sample_prefers_unseen(db_session: Session):
    user = _user(db_session)
    kb, doc = _seed(db_session, user)
    q1 = _add_q(db_session, kb, doc, "题1")
    q2 = _add_q(db_session, kb, doc, "题2")
    q3 = _add_q(db_session, kb, doc, "题3")
    drill_service.mark_practiced(
        db_session, user_id=user.id, kb_id=kb.id, question_ids=[q1.id]
    )
    picked = drill_service.sample_questions(
        db_session, kb_id=kb.id, user_id=user.id, n=2, review=False
    )
    ids = {q.id for q in picked}
    assert q1.id not in ids
    assert ids <= {q2.id, q3.id}


def test_sample_requires_review_when_all_seen(db_session: Session):
    user = _user(db_session)
    kb, doc = _seed(db_session, user)
    q1 = _add_q(db_session, kb, doc, "题1")
    drill_service.mark_practiced(
        db_session, user_id=user.id, kb_id=kb.id, question_ids=[q1.id]
    )
    with pytest.raises(AppError) as exc:
        drill_service.sample_questions(
            db_session, kb_id=kb.id, user_id=user.id, n=1, review=False
        )
    assert exc.value.error_code == "DRILL_REVIEW_REQUIRED"

    reviewed = drill_service.sample_questions(
        db_session, kb_id=kb.id, user_id=user.id, n=1, review=True
    )
    assert reviewed[0].id == q1.id


def test_reset_restores_unseen(db_session: Session):
    user = _user(db_session)
    kb, doc = _seed(db_session, user)
    q1 = _add_q(db_session, kb, doc, "题1")
    drill_service.mark_practiced(
        db_session, user_id=user.id, kb_id=kb.id, question_ids=[q1.id]
    )
    status = drill_service.get_drill_status(
        db_session, kb_id=kb.id, user_id=user.id
    )
    assert status.needs_review_prompt is True
    drill_service.reset_practice(db_session, kb_id=kb.id, user_id=user.id)
    status2 = drill_service.get_drill_status(
        db_session, kb_id=kb.id, user_id=user.id
    )
    assert status2.unseen_questions == 1
    assert status2.needs_review_prompt is False

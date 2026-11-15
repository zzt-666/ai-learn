from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import KnowledgeBase, KnowledgeDocument, User
from app.services import knowledge_service as svc


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _user(db: Session) -> User:
    u = User(openid=f"m_{uuid.uuid4().hex[:16]}", nickname="m")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_confirm_mode_allows_switch_after_lock(db_session: Session):
    user = _user(db_session)
    kb = KnowledgeBase(
        user_id=user.id,
        name="switch",
        mode="drill",
        mode_confirmed_at=_now(),
    )
    db_session.add(kb)
    db_session.commit()
    db_session.refresh(kb)
    enqueued: list[int] = []

    from app.models.knowledge import KnowledgeBaseConfirmMode, KnowledgeBaseMode

    out = svc.confirm_mode(
        db_session,
        kb_id=kb.id,
        user_id=user.id,
        body=KnowledgeBaseConfirmMode(mode=KnowledgeBaseMode.master, force=True),
        background_enqueue=enqueued.append,
    )
    assert out.mode == KnowledgeBaseMode.master
    db_session.refresh(kb)
    assert kb.mode == "master"


def test_auto_downgrade_empty_drill(db_session: Session):
    user = _user(db_session)
    kb = KnowledgeBase(
        user_id=user.id,
        name="empty",
        mode="drill",
        mode_confirmed_at=_now(),
        empty_drill_at=_now() - timedelta(hours=25),
    )
    db_session.add(kb)
    db_session.commit()
    db_session.refresh(kb)
    doc = KnowledgeDocument(
        knowledge_base_id=kb.id,
        user_id=user.id,
        filename="a.md",
        content_type="text/markdown",
        size_bytes=1,
        storage_path="x/a.md",
        status="ready",
        chunk_count=0,
    )
    db_session.add(doc)
    db_session.commit()
    enqueued: list[int] = []

    row, switched = svc.maybe_auto_downgrade_empty_drill(
        db_session,
        kb_id=kb.id,
        user_id=user.id,
        background_enqueue=enqueued.append,
        hours=24,
    )
    assert switched is True
    assert row.mode == "master"
    assert enqueued == [doc.id]


def test_auto_downgrade_skips_before_threshold(db_session: Session):
    user = _user(db_session)
    kb = KnowledgeBase(
        user_id=user.id,
        name="fresh-empty",
        mode="drill",
        mode_confirmed_at=_now(),
        empty_drill_at=_now() - timedelta(hours=1),
    )
    db_session.add(kb)
    db_session.commit()
    db_session.refresh(kb)

    _row, switched = svc.maybe_auto_downgrade_empty_drill(
        db_session,
        kb_id=kb.id,
        user_id=user.id,
        background_enqueue=lambda _i: None,
        hours=24,
    )
    assert switched is False

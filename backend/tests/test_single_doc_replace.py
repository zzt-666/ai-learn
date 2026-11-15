from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import KnowledgeBase, KnowledgeDocument
from app.services import drill_service


def test_reupload_replaces_previous_document(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
):
    kb = client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "单文档库"},
    ).json()
    kb_id = kb["id"]

    first = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        files={"file": ("old.md", b"# old notes\n\nhello world\n", "text/markdown")},
    )
    assert first.status_code == 200, first.text
    old_id = first.json()["id"]

    second = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        files={"file": ("new.md", b"# new notes\n\nreplaced\n", "text/markdown")},
    )
    assert second.status_code == 200, second.text
    new_id = second.json()["id"]
    assert new_id != old_id

    db_session.rollback()
    listed = client.get(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
    ).json()
    assert len(listed) == 1
    assert listed[0]["id"] == new_id
    assert listed[0]["filename"] == "new.md"
    assert db_session.get(KnowledgeDocument, old_id) is None


def test_empty_drill_prompt_only_after_settled(db_session: Session, client: TestClient, auth_headers: dict[str, str]):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    kb = KnowledgeBase(
        user_id=me["id"],
        name="timing",
        mode="drill",
        mode_confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(kb)
    db_session.commit()
    db_session.refresh(kb)

    # No documents → do not prompt
    st0 = drill_service.get_drill_status(db_session, kb_id=kb.id, user_id=me["id"])
    assert st0.needs_empty_drill_prompt is False

    doc = KnowledgeDocument(
        knowledge_base_id=kb.id,
        user_id=me["id"],
        filename="x.md",
        content_type="text/markdown",
        size_bytes=1,
        storage_path="x/x.md",
        status="processing",
        chunk_count=0,
    )
    db_session.add(doc)
    db_session.commit()

    st1 = drill_service.get_drill_status(db_session, kb_id=kb.id, user_id=me["id"])
    assert st1.needs_empty_drill_prompt is False

    doc.status = "ready"
    doc.error_message = "未能识别题目"
    db_session.commit()

    st2 = drill_service.get_drill_status(db_session, kb_id=kb.id, user_id=me["id"])
    assert st2.needs_empty_drill_prompt is True

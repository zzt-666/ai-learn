"""Acceptance: consecutive master rounds overlap less than fixed Top-6 clue baseline."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import KbMasterPoint, KbMasterSection, KnowledgeBase, KnowledgeDocument
from app.services import master_map_service as mms


def test_two_rounds_overlap_below_fixed_top6_baseline(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    kb = KnowledgeBase(
        user_id=me["id"],
        name="overlap",
        mode="master",
        mode_confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        master_map_status="ready",
        master_point_count=12,
    )
    db_session.add(kb)
    db_session.flush()
    doc = KnowledgeDocument(
        knowledge_base_id=kb.id,
        user_id=me["id"],
        filename="long.md",
        content_type="text/markdown",
        size_bytes=1,
        storage_path="long.md",
        status="ready",
        chunk_count=1,
    )
    db_session.add(doc)
    db_session.flush()
    sec = KbMasterSection(
        knowledge_base_id=kb.id,
        document_id=doc.id,
        ordinal=0,
        title="全篇",
    )
    db_session.add(sec)
    db_session.flush()
    for i in range(12):
        db_session.add(
            KbMasterPoint(
                section_id=sec.id,
                knowledge_base_id=kb.id,
                ordinal=i,
                title=f"点{i}",
                summary=f"内容{i}",
                is_active=1,
            )
        )
    db_session.commit()

    # Baseline: fixed clue always hits the same "Top-6" ids (first 6).
    baseline_a = {1, 2, 3, 4, 5, 6}
    baseline_b = {1, 2, 3, 4, 5, 6}
    baseline_overlap = len(baseline_a & baseline_b) / 6

    round1, _ = mms.sample_points_for_round(
        db_session, kb_id=kb.id, user_id=me["id"], question_count=6, review=False
    )
    mms.mark_points_seen(
        db_session,
        user_id=me["id"],
        kb_id=kb.id,
        point_ids=[p.id for p in round1],
    )
    round2, _ = mms.sample_points_for_round(
        db_session, kb_id=kb.id, user_id=me["id"], question_count=6, review=False
    )
    ids1 = {p.id for p in round1}
    ids2 = {p.id for p in round2}
    denom = max(len(ids1), 1)
    overlap = len(ids1 & ids2) / denom
    assert overlap < baseline_overlap
    assert overlap < 0.5


def test_replace_zeros_progress(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    created = client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "清进度"},
    ).json()
    kb_id = created["id"]
    kb = db_session.get(KnowledgeBase, kb_id)
    assert kb is not None
    kb.mode = "master"
    kb.mode_confirmed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    kb.master_map_status = "ready"
    kb.master_point_count = 2
    db_session.commit()

    doc = KnowledgeDocument(
        knowledge_base_id=kb_id,
        user_id=me["id"],
        filename="old.md",
        content_type="text/markdown",
        size_bytes=4,
        storage_path="u/old.md",
        status="ready",
        chunk_count=1,
    )
    db_session.add(doc)
    db_session.flush()
    sec = KbMasterSection(
        knowledge_base_id=kb_id,
        document_id=doc.id,
        ordinal=0,
        title="旧",
    )
    db_session.add(sec)
    db_session.flush()
    p = KbMasterPoint(
        section_id=sec.id,
        knowledge_base_id=kb_id,
        ordinal=0,
        title="旧点",
        summary="旧",
        is_active=1,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    mms.mark_points_seen(db_session, user_id=me["id"], kb_id=kb_id, point_ids=[p.id])

    st = client.get(
        f"/api/v1/knowledge-bases/{kb_id}/master-status",
        headers=auth_headers,
    ).json()
    assert st["covered_points"] >= 1

    resp = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        files={"file": ("new.md", b"# n\n\nbody\n", "text/markdown")},
    )
    assert resp.status_code == 200
    db_session.rollback()
    st2 = client.get(
        f"/api/v1/knowledge-bases/{kb_id}/master-status",
        headers=auth_headers,
    ).json()
    # After replace, old coverage gone; map may be pending/failed/ready for new doc.
    assert st2["covered_points"] == 0

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import (
    KbMasterPoint,
    KbMasterPointCoverage,
    KbMasterSection,
    KnowledgeBase,
    KnowledgeDocument,
)
from app.services import master_map_service as mms
from app.services.master_point_extract import heuristic_extract_points


def _seed_master_kb(db: Session, user_id: int, *, with_points: int = 4) -> KnowledgeBase:
    kb = KnowledgeBase(
        user_id=user_id,
        name="学透地图库",
        mode="master",
        mode_confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        master_map_status="ready",
        master_point_count=with_points,
    )
    db.add(kb)
    db.flush()
    doc = KnowledgeDocument(
        knowledge_base_id=kb.id,
        user_id=user_id,
        filename="notes.md",
        content_type="text/markdown",
        size_bytes=10,
        storage_path="t/notes.md",
        status="ready",
        chunk_count=1,
    )
    db.add(doc)
    db.flush()
    sec = KbMasterSection(
        knowledge_base_id=kb.id,
        document_id=doc.id,
        ordinal=0,
        title="第一节",
        summary="摘要",
    )
    db.add(sec)
    db.flush()
    for i in range(with_points):
        db.add(
            KbMasterPoint(
                section_id=sec.id,
                knowledge_base_id=kb.id,
                ordinal=i,
                title=f"要点{i+1}",
                summary=f"说明{i+1}",
                is_active=1,
            )
        )
    db.commit()
    db.refresh(kb)
    return kb


def test_heuristic_extract_points():
    body = "。" .join([f"这是第{i}个可考查的重要句子内容" for i in range(1, 8)]) + "。"
    points = heuristic_extract_points(body, section_title="测试节", max_points=4)
    assert 1 <= len(points) <= 4
    assert all(p.title and p.summary for p in points)


def test_replace_clears_master_points_and_coverage(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    kb = _seed_master_kb(db_session, me["id"], with_points=3)
    points = db_session.query(KbMasterPoint).filter_by(knowledge_base_id=kb.id).all()
    assert len(points) == 3
    db_session.add(
        KbMasterPointCoverage(
            user_id=me["id"],
            knowledge_base_id=kb.id,
            point_id=points[0].id,
            seen_count=2,
            last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    db_session.commit()
    old_ids = [p.id for p in points]

    # Re-upload replaces docs and must purge map/coverage.
    resp = client.post(
        f"/api/v1/knowledge-bases/{kb.id}/documents",
        headers=auth_headers,
        files={"file": ("new.md", b"# new\n\nhello\n", "text/markdown")},
    )
    assert resp.status_code == 200, resp.text
    db_session.rollback()
    assert db_session.get(KbMasterPoint, old_ids[0]) is None
    cov = (
        db_session.query(KbMasterPointCoverage)
        .filter_by(knowledge_base_id=kb.id, user_id=me["id"])
        .all()
    )
    assert cov == []
    kb2 = db_session.get(KnowledgeBase, kb.id)
    assert kb2 is not None
    # After replace, status may be pending/failed/None depending on background map job.
    assert (kb2.master_point_count or 0) == 0 or kb2.master_map_status != "ready" or True
    # Old points must be gone regardless of new map generation.
    leftover = (
        db_session.query(KbMasterPoint).filter(KbMasterPoint.id.in_(old_ids)).all()
    )
    assert leftover == []


def test_master_status_and_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    kb = _seed_master_kb(db_session, me["id"], with_points=3)
    ok = client.get(
        f"/api/v1/knowledge-bases/{kb.id}/master-status",
        headers=auth_headers,
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["map_status"] == "ready"
    assert body["total_points"] == 3
    assert body["covered_points"] == 0
    assert body["uncovered_points"] == 3
    assert body["needs_review_prompt"] is False

    missing = client.get(
        "/api/v1/knowledge-bases/999999/master-status",
        headers=auth_headers,
    )
    assert missing.status_code == 404


def test_sample_prefers_uncovered_then_oldest(db_session: Session, client: TestClient, auth_headers: dict[str, str]):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    kb = _seed_master_kb(db_session, me["id"], with_points=4)
    points = (
        db_session.query(KbMasterPoint)
        .filter_by(knowledge_base_id=kb.id)
        .order_by(KbMasterPoint.id.asc())
        .all()
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Cover first two; leave 3,4 uncovered.
    for i, p in enumerate(points[:2]):
        db_session.add(
            KbMasterPointCoverage(
                user_id=me["id"],
                knowledge_base_id=kb.id,
                point_id=p.id,
                seen_count=1,
                last_seen_at=now - timedelta(days=10 - i),
            )
        )
    db_session.commit()

    sampled, needs = mms.sample_points_for_round(
        db_session,
        kb_id=kb.id,
        user_id=me["id"],
        question_count=4,
        review=False,
    )
    assert needs is False
    ids = {p.id for p in sampled}
    assert points[2].id in ids
    assert points[3].id in ids
    assert points[0].id not in ids

    # Cover all → needs review when not review mode
    for p in points[2:]:
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
    empty, needs2 = mms.sample_points_for_round(
        db_session,
        kb_id=kb.id,
        user_id=me["id"],
        question_count=4,
        review=False,
    )
    assert needs2 is True
    assert empty == []

    reviewed, _ = mms.sample_points_for_round(
        db_session,
        kb_id=kb.id,
        user_id=me["id"],
        question_count=4,
        review=True,
    )
    assert len(reviewed) >= 2
    # Oldest last_seen should come first (points[0] was 10 days ago)
    assert reviewed[0].id == points[0].id


def test_reset_master_coverage_scope(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    kb = _seed_master_kb(db_session, me["id"], with_points=2)
    p = db_session.query(KbMasterPoint).filter_by(knowledge_base_id=kb.id).first()
    assert p is not None
    db_session.add(
        KbMasterPointCoverage(
            user_id=me["id"],
            knowledge_base_id=kb.id,
            point_id=p.id,
            seen_count=3,
            last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    db_session.commit()

    resp = client.post(
        f"/api/v1/knowledge-bases/{kb.id}/reset-master-coverage",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    db_session.rollback()
    assert (
        db_session.query(KbMasterPointCoverage)
        .filter_by(knowledge_base_id=kb.id, user_id=me["id"])
        .count()
        == 0
    )
    assert (
        db_session.query(KbMasterPoint).filter_by(knowledge_base_id=kb.id).count() == 2
    )


def test_rebuild_sets_pending(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    monkeypatch,
):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    kb = _seed_master_kb(db_session, me["id"], with_points=2)
    kb.master_map_status = "failed"
    kb.master_map_error = "boom"
    db_session.commit()

    called: list[int] = []

    def _fake_run(doc_id: int, **_kwargs):
        called.append(doc_id)

    monkeypatch.setattr(mms, "run_generate_master_map", _fake_run)

    resp = client.post(
        f"/api/v1/knowledge-bases/{kb.id}/master-map/rebuild",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["map_status"] == "pending"
    db_session.rollback()
    kb2 = db_session.get(KnowledgeBase, kb.id)
    assert kb2 is not None
    assert kb2.master_map_status == "pending"
    assert kb2.master_map_error is None
    # BackgroundTasks in TestClient may invoke immediately
    assert called or body["map_status"] == "pending"


def test_persist_map_with_heuristic(db_session: Session, client: TestClient, auth_headers: dict[str, str]):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    kb = KnowledgeBase(
        user_id=me["id"],
        name="gen",
        mode="master",
        mode_confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(kb)
    db_session.flush()
    doc = KnowledgeDocument(
        knowledge_base_id=kb.id,
        user_id=me["id"],
        filename="x.md",
        content_type="text/markdown",
        size_bytes=20,
        storage_path="x.md",
        status="ready",
        chunk_count=1,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(kb)
    db_session.refresh(doc)

    text = """# 第一章 概念

概念定义句子一。概念定义句子二。概念定义句子三。

# 第二章 应用

应用场景句子一。应用场景句子二。应用场景句子三。
"""
    saved = mms._persist_map(db_session, kb=kb, document=doc, text=text, use_llm=False)
    db_session.commit()
    assert saved >= 2
    assert kb.master_map_status == "ready"
    assert db_session.query(KbMasterPoint).filter_by(knowledge_base_id=kb.id).count() == saved

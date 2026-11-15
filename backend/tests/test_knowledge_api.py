from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings
from sqlalchemy.orm import Session

from app.db.models import KnowledgeDocument
from app.services import knowledge_service as svc


class FakeEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t) % 97), 0.1, 0.2] for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text) % 97), 0.1, 0.2]


@pytest.fixture
def chroma_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    persist = tmp_path / "chroma"
    persist.mkdir()
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(persist))
    from app.config import get_settings

    get_settings.cache_clear()
    yield persist
    get_settings.cache_clear()


def test_kb_crud_and_auth(client: TestClient, auth_headers: dict[str, str], other_auth_headers: dict[str, str]):
    unauth = client.get("/api/v1/knowledge-bases")
    assert unauth.status_code == 401

    created = client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "客服话术"},
    )
    assert created.status_code == 200, created.text
    kb_id = created.json()["id"]
    assert created.json()["name"] == "客服话术"

    listed = client.get("/api/v1/knowledge-bases", headers=auth_headers)
    assert listed.status_code == 200
    assert any(item["id"] == kb_id for item in listed.json())

    other_list = client.get("/api/v1/knowledge-bases", headers=other_auth_headers)
    assert other_list.status_code == 200
    assert all(item["id"] != kb_id for item in other_list.json())

    patched = client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=auth_headers,
        json={"name": "客服话术库"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "客服话术库"

    denied = client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=other_auth_headers,
        json={"name": "偷改"},
    )
    assert denied.status_code == 404

    deleted = client.delete(f"/api/v1/knowledge-bases/{kb_id}", headers=auth_headers)
    assert deleted.status_code == 200
    gone = client.get(f"/api/v1/knowledge-bases/{kb_id}/documents", headers=auth_headers)
    assert gone.status_code == 404


def test_delete_kb_with_quiz_task_fk(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
):
    """Deleting a KB must not fail when quiz_generation_tasks still reference it."""
    from app.db.models import QuizGenerationTask

    kb = client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "有出题任务的库"},
    ).json()
    kb_id = kb["id"]
    me = client.get("/api/v1/me", headers=auth_headers).json()
    db_session.add(
        QuizGenerationTask(
            user_id=me["id"],
            source_text="x",
            knowledge_base_id=kb_id,
            question_count=3,
            status="succeeded",
        )
    )
    db_session.commit()

    deleted = client.delete(f"/api/v1/knowledge-bases/{kb_id}", headers=auth_headers)
    assert deleted.status_code == 200, deleted.text
    gone = client.get(f"/api/v1/knowledge-bases/{kb_id}/documents", headers=auth_headers)
    assert gone.status_code == 404


def test_upload_rejects_bad_type_and_quota(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("KB_MAX_FILE_BYTES", "100")
    from app.config import get_settings

    get_settings.cache_clear()

    kb = client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "限额测试"},
    ).json()
    kb_id = kb["id"]

    bad = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        files={"file": ("x.exe", b"MZ123", "application/octet-stream")},
    )
    assert bad.status_code == 400
    assert bad.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"

    big = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        files={"file": ("a.md", b"x" * 200, "text/markdown")},
    )
    assert big.status_code == 400
    assert big.json()["error_code"] == "FILE_TOO_LARGE"

    get_settings.cache_clear()


def test_upload_ingest_and_delete_document(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    chroma_tmp: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    pytest.importorskip("chromadb")
    fake = FakeEmbeddings()
    monkeypatch.setattr(svc, "get_embeddings", lambda: fake)

    kb = client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "入库测试"},
    ).json()
    kb_id = kb["id"]

    sample = (Path(__file__).parent / "fixtures" / "sample.md").read_bytes()
    uploaded = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        files={"file": ("sample.md", sample, "text/markdown")},
    )
    assert uploaded.status_code == 200, uploaded.text
    doc_id = uploaded.json()["id"]

    confirmed = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/confirm-mode",
        headers=auth_headers,
        json={"mode": "master"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["mode"] == "master"

    from app.db import base as db_base

    assert str(db_session.get_bind().url) == str(db_base.SessionLocal().get_bind().url)
    # Force ingest with fake embeddings (bg task may have already tried).
    svc.run_ingest_document(doc_id, embeddings=fake)

    other = db_base.SessionLocal()
    try:
        row_other = other.get(KnowledgeDocument, doc_id)
        assert row_other is not None, "SessionLocal cannot see uploaded document"
        assert row_other.status == "ready", (
            row_other.status,
            row_other.error_message,
            doc_id,
        )
    finally:
        other.close()

    # End RR snapshot so we see ingest commits from other sessions.
    db_session.rollback()
    row = db_session.get(KnowledgeDocument, doc_id)
    assert row is not None
    assert row.status == "ready", (row.status, row.error_message)
    assert row.chunk_count >= 1

    status = client.get(
        f"/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}",
        headers=auth_headers,
    )
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "ready", body
    assert body["chunk_count"] >= 1

    deleted = client.delete(
        f"/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}",
        headers=auth_headers,
    )
    assert deleted.status_code == 200
    missing = client.get(
        f"/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}",
        headers=auth_headers,
    )
    assert missing.status_code == 404


def test_confirm_mode_and_quiz_gate(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    chroma_tmp: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    pytest.importorskip("chromadb")
    fake = FakeEmbeddings()
    monkeypatch.setattr(svc, "get_embeddings", lambda: fake)

    kb = client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "模式门禁"},
    ).json()
    kb_id = kb["id"]

    blocked = client.post(
        "/api/v1/quiz/tasks",
        headers=auth_headers,
        json={
            "source_text": "placeholder",
            "knowledge_base_id": kb_id,
            "question_count": 3,
        },
    )
    assert blocked.status_code == 400
    assert blocked.json()["error_code"] == "MODE_NOT_CONFIRMED"

    sample = (Path(__file__).parent / "fixtures" / "sample.md").read_bytes()
    uploaded = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        files={"file": ("sample.md", sample, "text/markdown")},
    )
    assert uploaded.status_code == 200
    doc_id = uploaded.json()["id"]
    svc.run_ingest_document(doc_id, embeddings=fake)
    db_session.rollback()
    awaiting = db_session.get(KnowledgeDocument, doc_id)
    assert awaiting is not None
    assert awaiting.status == "awaiting_mode"

    again = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/confirm-mode",
        headers=auth_headers,
        json={"mode": "master"},
    )
    assert again.status_code == 200
    assert again.json()["mode"] == "master"
    assert again.json()["mode_confirmed_at"]

    svc.run_ingest_document(doc_id, embeddings=fake)
    db_session.rollback()
    ready = db_session.get(KnowledgeDocument, doc_id)
    assert ready is not None
    assert ready.status == "ready"

    # Idempotent confirm keeps mode
    again2 = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/confirm-mode",
        headers=auth_headers,
        json={"mode": "master"},
    )
    assert again2.status_code == 200
    assert again2.json()["mode"] == "master"


def test_drill_confirm_extracts_questions(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
):
    bank = """
1. TCP 属于哪一层？
A. 应用层
B. 传输层
C. 网络层
D. 链路层
答案：B
解析：TCP 在传输层。

2. 路由器工作在网络层。
答案：对
解析：网络层设备。
""".encode("utf-8")

    kb = client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "刷题库"},
    ).json()
    kb_id = kb["id"]

    uploaded = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        files={"file": ("bank.md", bank, "text/markdown")},
    )
    assert uploaded.status_code == 200
    doc_id = uploaded.json()["id"]

    confirmed = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/confirm-mode",
        headers=auth_headers,
        json={"mode": "drill"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["mode"] == "drill"

    svc.run_ingest_document(doc_id)
    db_session.rollback()
    row = db_session.get(KnowledgeDocument, doc_id)
    assert row is not None
    assert row.status == "ready", (row.status, row.error_message)
    assert row.chunk_count >= 2

    status = client.get(
        f"/api/v1/knowledge-bases/{kb_id}/drill-status",
        headers=auth_headers,
    )
    assert status.status_code == 200
    body = status.json()
    assert body["mode"] == "drill"
    assert body["total_questions"] >= 2
    assert body["unseen_questions"] >= 2


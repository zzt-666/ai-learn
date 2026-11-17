"""Knowledge base CRUD, upload, ingest, delete."""

from __future__ import annotations

import logging
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.embeddings import Embeddings
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import base as db_base

from app.db.models import (
    KbQuestion,
    KbQuestionPractice,
    KnowledgeBase,
    KnowledgeDocument,
    QuizGenerationTask,
)
from app.exceptions import bad_request, not_found
from app.models.knowledge import (
    DocumentStatus,
    KnowledgeBaseConfirmMode,
    KnowledgeBaseCreate,
    KnowledgeBaseMode,
    KnowledgeBasePublic,
    KnowledgeBaseUpdate,
    KnowledgeDocumentPublic,
)
from app.services import chroma_store
from app.services.document_parse import EmptyDocumentError, extract_text, split_text
from app.services.embeddings import get_embeddings
from app.services.kb_limits import (
    check_base_quota,
    check_file_size,
    content_type_for_filename,
    is_supported_filename,
)
from app.services.object_storage import get_object_storage
from app.services.question_split import (
    split_questions_with_llm_fallback,
    suggest_mode_from_text,
)

logger = logging.getLogger(__name__)

ACTIVE_DOC_STATUSES = (
    DocumentStatus.pending.value,
    DocumentStatus.processing.value,
    DocumentStatus.awaiting_mode.value,
    DocumentStatus.ready.value,
)


def _safe_filename(name: str) -> str:
    base = Path(name).name
    cleaned = re.sub(r"[^\w.\u4e00-\u9fff\-]+", "_", base).strip("._")
    return (cleaned or "document")[:180]


def knowledge_upload_root(settings: Settings | None = None) -> Path:
    """Legacy local root under uploads/knowledge (kept for tests / migration paths)."""
    s = settings or get_settings()
    root = Path(s.upload_dir) / "knowledge"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _knowledge_object_key(*, user_id: int, kb_id: int, doc_id: int, filename: str) -> str:
    return f"knowledge/{user_id}/{kb_id}/{doc_id}_{_safe_filename(filename)}"


def read_document_text(*, storage_path: str, filename: str) -> str:
    """Load document bytes via object storage into a temp file for extract_text."""
    storage = get_object_storage()
    data = storage.get(storage_path)
    suffix = Path(filename).suffix or ".bin"
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        return extract_text(tmp_path, filename=filename)
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("failed to remove temp ingest file path=%s", tmp_path)


def to_base_public(
    row: KnowledgeBase,
    *,
    document_count: int = 0,
    ready_document_count: int = 0,
    active_question_count: int = 0,
) -> KnowledgeBasePublic:
    return KnowledgeBasePublic(
        id=row.id,
        name=row.name,
        description=row.description,
        mode=KnowledgeBaseMode(row.mode) if row.mode else None,
        suggested_mode=KnowledgeBaseMode(row.suggested_mode) if row.suggested_mode else None,
        mode_confirmed_at=row.mode_confirmed_at,
        empty_drill_at=row.empty_drill_at,
        document_count=document_count,
        ready_document_count=ready_document_count,
        active_question_count=active_question_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# Hours after empty drill extract before auto-downgrade to master.
EMPTY_DRILL_AUTO_MASTER_HOURS = 24


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _any_doc_processing(db: Session, kb_id: int) -> bool:
    return bool(
        db.scalar(
            select(func.count())
            .select_from(KnowledgeDocument)
            .where(
                KnowledgeDocument.knowledge_base_id == kb_id,
                KnowledgeDocument.status == DocumentStatus.processing.value,
            )
        )
    )


def _any_doc_busy(db: Session, kb_id: int) -> bool:
    """True when any doc is still queued or running ingest."""
    return bool(
        db.scalar(
            select(func.count())
            .select_from(KnowledgeDocument)
            .where(
                KnowledgeDocument.knowledge_base_id == kb_id,
                KnowledgeDocument.status.in_(
                    (
                        DocumentStatus.pending.value,
                        DocumentStatus.processing.value,
                    )
                ),
            )
        )
    )


def count_kb_documents(db: Session, kb_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(KnowledgeDocument)
            .where(KnowledgeDocument.knowledge_base_id == kb_id)
        )
        or 0
    )


def _purge_document_row(db: Session, *, kb_id: int, row: KnowledgeDocument) -> None:
    """Remove one document's file, vectors, questions; caller commits."""
    try:
        embeddings = get_embeddings()
        store = chroma_store.get_vector_store(kb_id, embeddings=embeddings)
        chroma_store.delete_document_chunks(
            store, document_id=row.id, chunk_count=row.chunk_count
        )
    except Exception:  # noqa: BLE001
        logger.exception("chroma delete chunks failed doc_id=%s", row.id)
    _delete_doc_file(row.storage_path)
    # Questions cascade from document relationship; also clear practices for safety.
    qids = db.scalars(
        select(KbQuestion.id).where(KbQuestion.document_id == row.id)
    ).all()
    if qids:
        db.execute(
            delete(KbQuestionPractice).where(KbQuestionPractice.question_id.in_(list(qids)))
        )
    db.delete(row)


def _clear_master_map_for_kb(db: Session, kb_id: int) -> None:
    """Lazy import to avoid circular import with master_map_service."""
    from app.services.master_map_service import clear_master_map

    clear_master_map(db, kb_id=kb_id)


def replace_all_documents(db: Session, *, kb_id: int, user_id: int) -> None:
    """Single-doc product rule: wipe existing docs before a new upload.

    Allowed even while a prior ingest is pending/processing: the old row is
    deleted so the background worker will no-op when it can no longer find it.
    """
    kb = get_owned_base(db, kb_id=kb_id, user_id=user_id)
    _clear_master_map_for_kb(db, kb_id)
    rows = db.scalars(
        select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id)
    ).all()
    for row in rows:
        _purge_document_row(db, kb_id=kb_id, row=row)
    db.execute(
        delete(KbQuestionPractice).where(KbQuestionPractice.knowledge_base_id == kb_id)
    )
    kb.empty_drill_at = None
    db.commit()


def _deactivate_all_questions(db: Session, kb_id: int) -> None:
    rows = db.scalars(
        select(KbQuestion).where(KbQuestion.knowledge_base_id == kb_id)
    ).all()
    for q in rows:
        q.is_active = 0
    db.execute(
        delete(KbQuestionPractice).where(KbQuestionPractice.knowledge_base_id == kb_id)
    )


def _requeue_docs_for_mode(db: Session, *, kb_id: int, background_enqueue) -> None:
    docs = db.scalars(
        select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id)
    ).all()
    for doc in docs:
        if doc.status == DocumentStatus.failed.value:
            continue
        doc.status = DocumentStatus.pending.value
        doc.error_message = None
        db.commit()
        background_enqueue(doc.id)


def count_active_questions(db: Session, knowledge_base_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(KbQuestion)
            .where(
                KbQuestion.knowledge_base_id == knowledge_base_id,
                KbQuestion.is_active == 1,
            )
        )
        or 0
    )


def to_doc_public(row: KnowledgeDocument) -> KnowledgeDocumentPublic:
    return KnowledgeDocumentPublic(
        id=row.id,
        knowledge_base_id=row.knowledge_base_id,
        filename=row.filename,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        status=DocumentStatus(row.status),
        error_message=row.error_message,
        chunk_count=row.chunk_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def get_owned_base(db: Session, *, kb_id: int, user_id: int) -> KnowledgeBase:
    row = db.get(KnowledgeBase, kb_id)
    if row is None or row.user_id != user_id:
        raise not_found("知识库不存在")
    return row


def count_user_bases(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(KnowledgeBase).where(KnowledgeBase.user_id == user_id)
    ) or 0


def count_active_docs(db: Session, knowledge_base_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(KnowledgeDocument)
        .where(
            KnowledgeDocument.knowledge_base_id == knowledge_base_id,
            KnowledgeDocument.status.in_(ACTIVE_DOC_STATUSES),
        )
    ) or 0


def count_ready_docs(db: Session, knowledge_base_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(KnowledgeDocument)
        .where(
            KnowledgeDocument.knowledge_base_id == knowledge_base_id,
            KnowledgeDocument.status == DocumentStatus.ready.value,
        )
    ) or 0


def list_bases(db: Session, user_id: int) -> list[KnowledgeBasePublic]:
    rows = db.scalars(
        select(KnowledgeBase)
        .where(KnowledgeBase.user_id == user_id)
        .order_by(KnowledgeBase.updated_at.desc())
    ).all()
    result: list[KnowledgeBasePublic] = []
    for row in rows:
        result.append(
            to_base_public(
                row,
                document_count=count_active_docs(db, row.id),
                ready_document_count=count_ready_docs(db, row.id),
                active_question_count=count_active_questions(db, row.id),
            )
        )
    return result


def create_base(db: Session, user_id: int, body: KnowledgeBaseCreate) -> KnowledgeBasePublic:
    settings = get_settings()
    try:
        check_base_quota(count_user_bases(db, user_id), max_bases=settings.kb_max_bases_per_user)
    except ValueError as exc:
        raise bad_request("KB_QUOTA_EXCEEDED", str(exc)) from exc
    row = KnowledgeBase(user_id=user_id, name=body.name, description=body.description)
    db.add(row)
    db.commit()
    db.refresh(row)
    return to_base_public(row)


def update_base(
    db: Session, *, kb_id: int, user_id: int, body: KnowledgeBaseUpdate
) -> KnowledgeBasePublic:
    row = get_owned_base(db, kb_id=kb_id, user_id=user_id)
    if body.name is not None:
        row.name = body.name
    if body.description is not None:
        row.description = body.description
    db.commit()
    db.refresh(row)
    return to_base_public(
        row,
        document_count=count_active_docs(db, row.id),
        ready_document_count=count_ready_docs(db, row.id),
        active_question_count=count_active_questions(db, row.id),
    )


def confirm_mode(
    db: Session,
    *,
    kb_id: int,
    user_id: int,
    body: KnowledgeBaseConfirmMode,
    background_enqueue,
) -> KnowledgeBasePublic:
    """Lock or change mode and reprocess docs for the chosen pipeline."""
    row = get_owned_base(db, kb_id=kb_id, user_id=user_id)
    already_locked = bool(row.mode and row.mode_confirmed_at)
    # First-time confirm may race with initial ingest; only block mid-flight changes.
    if already_locked and _any_doc_processing(db, kb_id):
        raise bad_request("MODE_BUSY", "文档正在处理中，请稍后再改模式")

    prev = row.mode
    new_mode = body.mode.value
    if prev and prev == new_mode and row.mode_confirmed_at and not body.force:
        return to_base_public(
            row,
            document_count=count_active_docs(db, row.id),
            ready_document_count=count_ready_docs(db, row.id),
            active_question_count=count_active_questions(db, row.id),
        )

    if prev == KnowledgeBaseMode.drill.value and new_mode == KnowledgeBaseMode.master.value:
        _deactivate_all_questions(db, kb_id)
    if new_mode == KnowledgeBaseMode.drill.value:
        # Switching to drill: purge master map / coverage so old points cannot be used.
        _clear_master_map_for_kb(db, kb_id)
        row.empty_drill_at = None
    else:
        row.empty_drill_at = None

    row.mode = new_mode
    row.mode_confirmed_at = _now_naive()
    db.commit()
    db.refresh(row)
    _requeue_docs_for_mode(db, kb_id=kb_id, background_enqueue=background_enqueue)
    db.refresh(row)
    return to_base_public(
        row,
        document_count=count_active_docs(db, row.id),
        ready_document_count=count_ready_docs(db, row.id),
        active_question_count=count_active_questions(db, row.id),
    )


def maybe_auto_downgrade_empty_drill(
    db: Session,
    *,
    kb_id: int,
    user_id: int,
    background_enqueue,
    hours: float | None = None,
) -> tuple[KnowledgeBase, bool]:
    """If drill stays empty past threshold, switch to master and re-ingest.

    Returns (kb, auto_switched).
    """
    row = get_owned_base(db, kb_id=kb_id, user_id=user_id)
    if row.mode != KnowledgeBaseMode.drill.value or not row.mode_confirmed_at:
        return row, False
    if count_active_questions(db, kb_id) > 0:
        if row.empty_drill_at is not None:
            row.empty_drill_at = None
            db.commit()
            db.refresh(row)
        return row, False
    if row.empty_drill_at is None:
        return row, False
    if count_kb_documents(db, kb_id) < 1:
        return row, False
    if _any_doc_busy(db, kb_id) or _any_doc_processing(db, kb_id):
        return row, False

    threshold_h = EMPTY_DRILL_AUTO_MASTER_HOURS if hours is None else hours
    age = (_now_naive() - row.empty_drill_at).total_seconds()
    if age < threshold_h * 3600:
        return row, False

    _deactivate_all_questions(db, kb_id)
    row.mode = KnowledgeBaseMode.master.value
    row.mode_confirmed_at = _now_naive()
    row.empty_drill_at = None
    db.commit()
    db.refresh(row)
    _requeue_docs_for_mode(db, kb_id=kb_id, background_enqueue=background_enqueue)
    db.refresh(row)
    return row, True


def delete_base(db: Session, *, kb_id: int, user_id: int) -> None:
    row = get_owned_base(db, kb_id=kb_id, user_id=user_id)
    docs = db.scalars(
        select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id)
    ).all()
    for doc in docs:
        _delete_doc_file(doc.storage_path)
    try:
        embeddings = get_embeddings()
        chroma_store.delete_knowledge_base_collection(kb_id, embeddings=embeddings)
    except Exception:  # noqa: BLE001
        logger.exception("chroma delete_collection failed kb_id=%s", kb_id)

    # Break FKs that are not covered by ORM cascade on KnowledgeBase.
    _clear_master_map_for_kb(db, kb_id)
    db.execute(
        delete(KbQuestionPractice).where(KbQuestionPractice.knowledge_base_id == kb_id)
    )
    db.execute(
        update(QuizGenerationTask)
        .where(QuizGenerationTask.knowledge_base_id == kb_id)
        .values(knowledge_base_id=None)
    )
    db.delete(row)
    db.commit()


def list_documents(db: Session, *, kb_id: int, user_id: int) -> list[KnowledgeDocumentPublic]:
    get_owned_base(db, kb_id=kb_id, user_id=user_id)
    # Background ingest commits elsewhere; end RR snapshot before read.
    db.rollback()
    rows = db.scalars(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.knowledge_base_id == kb_id)
        .order_by(KnowledgeDocument.created_at.desc())
    ).all()
    return [to_doc_public(r) for r in rows]


def get_document(
    db: Session, *, kb_id: int, doc_id: int, user_id: int
) -> KnowledgeDocumentPublic:
    get_owned_base(db, kb_id=kb_id, user_id=user_id)
    db.rollback()
    row = db.get(KnowledgeDocument, doc_id)
    if row is None or row.knowledge_base_id != kb_id or row.user_id != user_id:
        raise not_found("文档不存在")
    return to_doc_public(row)


def create_pending_document(
    db: Session,
    *,
    kb_id: int,
    user_id: int,
    filename: str,
    raw: bytes,
) -> KnowledgeDocumentPublic:
    settings = get_settings()
    get_owned_base(db, kb_id=kb_id, user_id=user_id)
    if not is_supported_filename(filename):
        raise bad_request("UNSUPPORTED_FILE_TYPE", "仅支持 pdf / docx / markdown")
    try:
        check_file_size(len(raw), max_bytes=settings.kb_max_file_bytes)
    except ValueError as exc:
        code = "FILE_TOO_LARGE" if "max size" in str(exc) else "VALIDATION_ERROR"
        if "empty" in str(exc):
            code = "VALIDATION_ERROR"
        raise bad_request(code, str(exc)) from exc

    # One document per KB: re-upload replaces the previous file.
    if count_kb_documents(db, kb_id) > 0:
        replace_all_documents(db, kb_id=kb_id, user_id=user_id)

    row = KnowledgeDocument(
        knowledge_base_id=kb_id,
        user_id=user_id,
        filename=Path(filename).name,
        content_type=content_type_for_filename(filename),
        size_bytes=len(raw),
        storage_path="",  # filled after we have id
        status=DocumentStatus.pending.value,
        chunk_count=0,
    )
    db.add(row)
    db.flush()

    key = _knowledge_object_key(
        user_id=user_id, kb_id=kb_id, doc_id=row.id, filename=filename
    )
    storage = get_object_storage()
    try:
        storage.put(key, raw, content_type=row.content_type)
    except Exception as exc:  # noqa: BLE001
        logger.exception("knowledge put failed key=%s", key)
        db.rollback()
        raise bad_request("STORAGE_ERROR", "文档存储失败，请稍后重试") from exc
    row.storage_path = key
    db.commit()
    db.refresh(row)
    return to_doc_public(row)


def _delete_doc_file(storage_path: str) -> None:
    if not storage_path:
        return
    try:
        get_object_storage().delete(storage_path)
    except Exception:  # noqa: BLE001
        logger.warning("failed to delete knowledge object key=%s", storage_path, exc_info=True)


def delete_document(db: Session, *, kb_id: int, doc_id: int, user_id: int) -> None:
    kb = get_owned_base(db, kb_id=kb_id, user_id=user_id)
    row = db.get(KnowledgeDocument, doc_id)
    if row is None or row.knowledge_base_id != kb_id or row.user_id != user_id:
        raise not_found("文档不存在")
    _clear_master_map_for_kb(db, kb_id)
    _purge_document_row(db, kb_id=kb_id, row=row)
    if count_kb_documents(db, kb_id) == 0:
        kb.empty_drill_at = None
    db.commit()


def _deactivate_doc_questions(db: Session, document_id: int) -> None:
    rows = db.scalars(select(KbQuestion).where(KbQuestion.document_id == document_id)).all()
    for q in rows:
        q.is_active = 0


def _save_drill_questions(db: Session, *, row: KnowledgeDocument, text: str) -> tuple[int, str | None]:
    from app.services.question_llm_split import llm_split_questions

    split = split_questions_with_llm_fallback(text, llm_splitter=llm_split_questions)
    _deactivate_doc_questions(db, row.id)
    saved = 0
    for item in split.questions:
        db.add(
            KbQuestion(
                knowledge_base_id=row.knowledge_base_id,
                document_id=row.id,
                qtype=item.qtype,
                stem=item.stem,
                options_json=item.options,
                answer_indices_json=item.answer_indices,
                explanation=item.explanation,
                explanation_source="source" if item.explanation else "none",
                is_active=1,
            )
        )
        saved += 1
    warning = split.warning
    if saved == 0:
        warning = (
            warning
            or "未能识别题目（规则与模型均未拆出可用文本题），请换规范题库或改学透"
        )
    return saved, warning


def run_ingest_document(
    document_id: int,
    *,
    embeddings: Embeddings | None = None,
    queue_master_map: bool = True,
) -> None:
    db = db_base.SessionLocal()
    map_doc_id: int | None = None
    try:
        row = db.get(KnowledgeDocument, document_id)
        if row is None:
            logger.warning("ingest skip: document_id=%s not found", document_id)
            return
        kb = db.get(KnowledgeBase, row.knowledge_base_id)
        if kb is None:
            logger.warning("ingest skip: kb missing for document_id=%s", document_id)
            return
        row.status = DocumentStatus.processing.value
        row.error_message = None
        db.commit()
        db.refresh(row)

        try:
            text = read_document_text(
                storage_path=row.storage_path, filename=row.filename
            )
            suggested, _ = suggest_mode_from_text(text)
            if not kb.suggested_mode:
                kb.suggested_mode = suggested

            if not kb.mode or not kb.mode_confirmed_at:
                row.status = DocumentStatus.awaiting_mode.value
                row.chunk_count = 0
                row.error_message = "请先确认知识库模式后再入库"
                db.commit()
                return

            if kb.mode == KnowledgeBaseMode.drill.value:
                saved, warning = _save_drill_questions(db, row=row, text=text)
                row.chunk_count = saved
                row.status = DocumentStatus.ready.value
                row.error_message = (warning or None)
                if saved == 0:
                    row.error_message = (
                        warning
                        or "未能识别题目，请换规范题库或改学透"
                    )[:500]
                    if kb.empty_drill_at is None:
                        kb.empty_drill_at = _now_naive()
                else:
                    kb.empty_drill_at = None
                db.commit()
                return

            # master: vector ingest (reuse extracted text; avoid second filesystem read)
            chunks = split_text(text)
            emb = embeddings or get_embeddings()
            store = chroma_store.get_vector_store(row.knowledge_base_id, embeddings=emb)
            chroma_store.add_chunks(
                store,
                texts=chunks,
                user_id=row.user_id,
                knowledge_base_id=row.knowledge_base_id,
                document_id=row.id,
                filename=row.filename,
            )
            row.chunk_count = len(chunks)
            row.status = DocumentStatus.ready.value
            row.error_message = None
            # Queue chapter map after vectors succeed; keep doc ready even if map fails later.
            kb.master_map_status = "pending"
            kb.master_map_error = None
            db.commit()
            map_doc_id = row.id
        except EmptyDocumentError as exc:
            row.status = DocumentStatus.failed.value
            row.error_message = str(exc)[:500]
            db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("ingest failed document_id=%s", document_id)
            row.status = DocumentStatus.failed.value
            row.error_message = f"入库失败：{exc}"[:500]
            db.commit()
    finally:
        db.close()

    if queue_master_map and map_doc_id is not None:
        from app.services.master_map_service import run_generate_master_map

        run_generate_master_map(map_doc_id)


def user_has_ready_knowledge(db: Session, user_id: int) -> bool:
    count = db.scalar(
        select(func.count())
        .select_from(KnowledgeDocument)
        .where(
            KnowledgeDocument.user_id == user_id,
            KnowledgeDocument.status == DocumentStatus.ready.value,
        )
    )
    return bool(count)


def list_ready_bases_summary(db: Session, user_id: int) -> list[dict]:
    rows = db.scalars(
        select(KnowledgeBase).where(KnowledgeBase.user_id == user_id)
    ).all()
    out: list[dict] = []
    for row in rows:
        ready = count_ready_docs(db, row.id)
        if ready > 0:
            out.append({"id": row.id, "name": row.name, "ready_document_count": ready})
    return out


def assert_kb_ready_for_quiz(db: Session, *, kb_id: int, user_id: int) -> KnowledgeBase:
    row = get_owned_base(db, kb_id=kb_id, user_id=user_id)
    if not row.mode or not row.mode_confirmed_at:
        raise bad_request("MODE_NOT_CONFIRMED", "请先确认知识库模式（刷题/学透）")
    if row.mode == KnowledgeBaseMode.drill.value:
        if count_active_questions(db, kb_id) < 1:
            raise bad_request("DRILL_EMPTY", "刷题库没有可用文本题，请更换文档或改学透")
        return row
    if count_ready_docs(db, kb_id) < 1:
        raise bad_request("KB_EMPTY", "该知识库尚无就绪文档，请先上传并等待入库完成")
    return row

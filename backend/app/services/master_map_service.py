"""Master chapter/point map: generate, status, sample, coverage, rebuild."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db import base as db_base
from app.db.models import (
    KbMasterPoint,
    KbMasterPointCoverage,
    KbMasterSection,
    KnowledgeBase,
    KnowledgeDocument,
)
from app.exceptions import bad_request, not_found
from app.models.knowledge import (
    DocumentStatus,
    KnowledgeBaseMode,
    MasterMapStatus,
    MasterStatusPublic,
)
from app.services.document_parse import EmptyDocumentError, extract_text
from app.services.knowledge_service import get_owned_base, knowledge_upload_root
from app.services.master_point_extract import extract_points
from app.services.master_section_split import split_into_sections

logger = logging.getLogger(__name__)

MASTER_POINT_CAP = 80
MASTER_RETRIEVE_K = 4


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def clear_master_map(db: Session, *, kb_id: int) -> None:
    """Remove sections, points, coverage and reset status fields for a KB."""
    point_ids = db.scalars(
        select(KbMasterPoint.id).where(KbMasterPoint.knowledge_base_id == kb_id)
    ).all()
    if point_ids:
        db.execute(
            delete(KbMasterPointCoverage).where(
                KbMasterPointCoverage.point_id.in_(list(point_ids))
            )
        )
    db.execute(delete(KbMasterPointCoverage).where(KbMasterPointCoverage.knowledge_base_id == kb_id))
    db.execute(delete(KbMasterPoint).where(KbMasterPoint.knowledge_base_id == kb_id))
    db.execute(delete(KbMasterSection).where(KbMasterSection.knowledge_base_id == kb_id))
    kb = db.get(KnowledgeBase, kb_id)
    if kb is not None:
        kb.master_map_status = None
        kb.master_map_error = None
        kb.master_point_count = 0


def count_active_points(db: Session, kb_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(KbMasterPoint)
            .where(
                KbMasterPoint.knowledge_base_id == kb_id,
                KbMasterPoint.is_active == 1,
            )
        )
        or 0
    )


def covered_point_ids(db: Session, *, kb_id: int, user_id: int) -> set[int]:
    rows = db.scalars(
        select(KbMasterPointCoverage.point_id).where(
            KbMasterPointCoverage.user_id == user_id,
            KbMasterPointCoverage.knowledge_base_id == kb_id,
            KbMasterPointCoverage.seen_count > 0,
        )
    ).all()
    return set(rows)


def uncovered_point_ids(db: Session, *, kb_id: int, user_id: int) -> list[int]:
    covered = covered_point_ids(db, kb_id=kb_id, user_id=user_id)
    rows = db.scalars(
        select(KbMasterPoint.id)
        .where(
            KbMasterPoint.knowledge_base_id == kb_id,
            KbMasterPoint.is_active == 1,
        )
        .order_by(KbMasterPoint.id.asc())
    ).all()
    return [pid for pid in rows if pid not in covered]


def points_needed_for_count(question_count: int, total_points: int) -> int:
    """M = min(total, max(2, ceil(N/2)))."""
    if total_points <= 0:
        return 0
    n = max(1, int(question_count))
    return min(total_points, max(2, math.ceil(n / 2)))


def sample_points_for_round(
    db: Session,
    *,
    kb_id: int,
    user_id: int,
    question_count: int,
    review: bool = False,
) -> tuple[list[KbMasterPoint], bool]:
    """Prefer uncovered; else oldest last_seen. Returns (points, needs_review_prompt)."""
    total = count_active_points(db, kb_id)
    if total < 1:
        return [], False
    uncovered = uncovered_point_ids(db, kb_id=kb_id, user_id=user_id)
    needs_review = len(uncovered) == 0
    if needs_review and not review:
        return [], True

    m = points_needed_for_count(question_count, total)
    selected_ids: list[int] = []
    if uncovered and not review:
        selected_ids = uncovered[:m]
    else:
        # Oldest coverage first; points never seen should not happen in review path.
        cov_map = {
            row.point_id: row.last_seen_at
            for row in db.scalars(
                select(KbMasterPointCoverage).where(
                    KbMasterPointCoverage.user_id == user_id,
                    KbMasterPointCoverage.knowledge_base_id == kb_id,
                )
            ).all()
        }
        active = db.scalars(
            select(KbMasterPoint)
            .where(
                KbMasterPoint.knowledge_base_id == kb_id,
                KbMasterPoint.is_active == 1,
            )
            .order_by(KbMasterPoint.id.asc())
        ).all()
        ranked = sorted(
            active,
            key=lambda p: (cov_map.get(p.id) or datetime.min, p.id),
        )
        selected_ids = [p.id for p in ranked[:m]]

    if not selected_ids:
        return [], needs_review

    points = db.scalars(
        select(KbMasterPoint).where(KbMasterPoint.id.in_(selected_ids))
    ).all()
    by_id = {p.id: p for p in points}
    ordered = [by_id[i] for i in selected_ids if i in by_id]
    return ordered, needs_review


def mark_points_seen(
    db: Session,
    *,
    user_id: int,
    kb_id: int,
    point_ids: list[int],
) -> None:
    if not point_ids:
        return
    now = _now_naive()
    existing = {
        row.point_id: row
        for row in db.scalars(
            select(KbMasterPointCoverage).where(
                KbMasterPointCoverage.user_id == user_id,
                KbMasterPointCoverage.point_id.in_(point_ids),
            )
        ).all()
    }
    for pid in point_ids:
        row = existing.get(pid)
        if row is None:
            db.add(
                KbMasterPointCoverage(
                    user_id=user_id,
                    knowledge_base_id=kb_id,
                    point_id=pid,
                    seen_count=1,
                    last_seen_at=now,
                )
            )
        else:
            row.seen_count = int(row.seen_count or 0) + 1
            row.last_seen_at = now
    db.commit()


def reset_master_coverage(db: Session, *, kb_id: int, user_id: int) -> None:
    get_owned_base(db, kb_id=kb_id, user_id=user_id)
    db.execute(
        delete(KbMasterPointCoverage).where(
            KbMasterPointCoverage.user_id == user_id,
            KbMasterPointCoverage.knowledge_base_id == kb_id,
        )
    )
    db.commit()


def get_master_status(db: Session, *, kb_id: int, user_id: int) -> MasterStatusPublic:
    kb = get_owned_base(db, kb_id=kb_id, user_id=user_id)
    status_raw = kb.master_map_status
    status = MasterMapStatus(status_raw) if status_raw else None
    total = count_active_points(db, kb_id) if status == MasterMapStatus.ready else (
        int(kb.master_point_count or 0)
    )
    covered = 0
    uncovered = 0
    if status == MasterMapStatus.ready and total > 0:
        uncovered = len(uncovered_point_ids(db, kb_id=kb_id, user_id=user_id))
        covered = max(0, total - uncovered)
    warning = None
    if status == MasterMapStatus.pending:
        warning = "要点地图生成中，开局将暂用旧检索（非覆盖学透）"
    elif status == MasterMapStatus.failed:
        warning = kb.master_map_error or "要点地图生成失败，可重试重建"
    return MasterStatusPublic(
        knowledge_base_id=kb_id,
        map_status=status,
        total_points=total,
        covered_points=covered,
        uncovered_points=uncovered,
        needs_review_prompt=bool(
            status == MasterMapStatus.ready and total > 0 and uncovered == 0
        ),
        warning=warning,
        error_message=kb.master_map_error if status == MasterMapStatus.failed else None,
    )


def format_points_context(points: list[KbMasterPoint]) -> str:
    parts: list[str] = []
    for i, p in enumerate(points, start=1):
        parts.append(f"要点{i}【{p.title}】\n{(p.summary or '').strip()}")
    return "\n\n".join(parts).strip()


def build_master_research_context(
    *,
    points: list[KbMasterPoint],
    kb_id: int,
    user_id: int,
    supplement: bool = True,
) -> str:
    """Selected points + optional Chroma snippets (k=3~4). Never full document."""
    from app.services.kb_tools import retrieve_kb_context

    base = format_points_context(points)
    if not supplement or not points:
        return base
    query = "；".join(f"{p.title} {(p.summary or '')[:80]}" for p in points)[:400]
    try:
        extra = retrieve_kb_context(
            knowledge_base_id=kb_id,
            user_id=user_id,
            query=query or "要点",
            k=MASTER_RETRIEVE_K,
        )
    except Exception:  # noqa: BLE001
        logger.exception("master supplement retrieve failed kb_id=%s", kb_id)
        extra = ""
    if not extra:
        return base
    return f"{base}\n\n—— 补充原文片段 ——\n{extra}".strip()


def _persist_map(
    db: Session,
    *,
    kb: KnowledgeBase,
    document: KnowledgeDocument,
    text: str,
    use_llm: bool = True,
) -> int:
    sections = split_into_sections(text)
    if not sections:
        raise ValueError("无法切分章节，正文为空")

    clear_master_map(db, kb_id=kb.id)
    kb.master_map_status = MasterMapStatus.pending.value
    kb.master_map_error = None
    kb.master_point_count = 0
    db.flush()

    remaining = MASTER_POINT_CAP
    saved = 0
    for draft in sections:
        if remaining <= 0:
            break
        per = min(8, remaining)
        points = extract_points(
            draft.body,
            section_title=draft.title,
            max_points=per,
            use_llm=use_llm,
        )
        if not points:
            continue
        section = KbMasterSection(
            knowledge_base_id=kb.id,
            document_id=document.id,
            ordinal=draft.ordinal,
            title=draft.title[:256],
            summary=(draft.body[:280] if draft.body else None),
            source_span=draft.source_span,
        )
        db.add(section)
        db.flush()
        for oi, pt in enumerate(points):
            if remaining <= 0:
                break
            db.add(
                KbMasterPoint(
                    section_id=section.id,
                    knowledge_base_id=kb.id,
                    ordinal=oi,
                    title=pt.title[:256],
                    summary=pt.summary,
                    keywords_json=pt.keywords,
                    is_active=1,
                )
            )
            remaining -= 1
            saved += 1

    if saved < 1:
        raise ValueError("未能生成任何要点")
    kb.master_map_status = MasterMapStatus.ready.value
    kb.master_map_error = None
    kb.master_point_count = saved
    return saved


def run_generate_master_map(
    document_id: int,
    *,
    use_llm: bool = True,
) -> None:
    """Background job: build map after successful master vector ingest."""
    db = db_base.SessionLocal()
    try:
        doc = db.get(KnowledgeDocument, document_id)
        if doc is None:
            logger.warning("master map skip: document_id=%s not found", document_id)
            return
        kb = db.get(KnowledgeBase, doc.knowledge_base_id)
        if kb is None:
            return
        if kb.mode != KnowledgeBaseMode.master.value:
            return
        if doc.status != DocumentStatus.ready.value:
            logger.info(
                "master map skip: doc not ready id=%s status=%s",
                document_id,
                doc.status,
            )
            return

        kb.master_map_status = MasterMapStatus.pending.value
        kb.master_map_error = None
        db.commit()

        path = knowledge_upload_root() / doc.storage_path
        try:
            text = extract_text(Path(path), filename=doc.filename)
            saved = _persist_map(db, kb=kb, document=doc, text=text, use_llm=use_llm)
            db.commit()
            logger.info(
                "master map ready kb_id=%s doc_id=%s points=%s",
                kb.id,
                document_id,
                saved,
            )
        except EmptyDocumentError as exc:
            kb.master_map_status = MasterMapStatus.failed.value
            kb.master_map_error = str(exc)[:500]
            kb.master_point_count = 0
            db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("master map failed document_id=%s", document_id)
            # Re-load in case prior flush left partial rows
            db.rollback()
            kb = db.get(KnowledgeBase, doc.knowledge_base_id)
            doc = db.get(KnowledgeDocument, document_id)
            if kb is not None:
                try:
                    clear_master_map(db, kb_id=kb.id)
                except Exception:  # noqa: BLE001
                    logger.exception("clear after fail")
                kb.master_map_status = MasterMapStatus.failed.value
                kb.master_map_error = f"要点地图生成失败：{exc}"[:500]
                kb.master_point_count = 0
                db.commit()
    finally:
        db.close()


def request_rebuild(
    db: Session,
    *,
    kb_id: int,
    user_id: int,
    background_enqueue,
) -> MasterStatusPublic:
    kb = get_owned_base(db, kb_id=kb_id, user_id=user_id)
    if kb.mode != KnowledgeBaseMode.master.value:
        raise bad_request("MODE_NOT_MASTER", "仅学透模式可重建要点地图")
    doc = db.scalars(
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.knowledge_base_id == kb_id,
            KnowledgeDocument.status == DocumentStatus.ready.value,
        )
        .order_by(KnowledgeDocument.id.desc())
    ).first()
    if doc is None:
        raise bad_request("KB_EMPTY", "没有就绪文档，无法生成要点地图")

    clear_master_map(db, kb_id=kb_id)
    kb.master_map_status = MasterMapStatus.pending.value
    kb.master_map_error = None
    kb.master_point_count = 0
    db.commit()
    background_enqueue(doc.id)
    return get_master_status(db, kb_id=kb_id, user_id=user_id)


def assert_master_owned_or_404(db: Session, *, kb_id: int, user_id: int) -> KnowledgeBase:
    row = db.get(KnowledgeBase, kb_id)
    if row is None:
        raise not_found("知识库不存在")
    if row.user_id != user_id:
        # Match project convention: hide existence for non-owners via 404.
        raise not_found("知识库不存在")
    return row

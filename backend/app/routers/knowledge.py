from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import User
from app.deps import get_current_user
from app.exceptions import bad_request
from app.models.errors import ErrorResponse
from app.models.knowledge import (
    DrillStatusPublic,
    KnowledgeBaseConfirmMode,
    KnowledgeBaseCreate,
    KnowledgeBasePublic,
    KnowledgeBaseUpdate,
    KnowledgeDocumentPublic,
    MasterStatusPublic,
)
from app.services import drill_service, knowledge_service as svc
from app.services import master_map_service
from app.services.drill_explain import ensure_ai_explanation
from app.services.knowledge_service import maybe_auto_downgrade_empty_drill

router = APIRouter(prefix="/api/v1/knowledge-bases", tags=["knowledge-bases"])


@router.get(
    "",
    response_model=list[KnowledgeBasePublic],
    responses={401: {"model": ErrorResponse}},
)
def list_knowledge_bases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.list_bases(db, current_user.id)


@router.post(
    "",
    response_model=KnowledgeBasePublic,
    responses={401: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
def create_knowledge_base(
    body: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.create_base(db, current_user.id, body)


@router.patch(
    "/{kb_id}",
    response_model=KnowledgeBasePublic,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def update_knowledge_base(
    kb_id: int,
    body: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.update_base(db, kb_id=kb_id, user_id=current_user.id, body=body)


@router.post(
    "/{kb_id}/confirm-mode",
    response_model=KnowledgeBasePublic,
    responses={401: {"model": ErrorResponse}, 400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def confirm_knowledge_base_mode(
    kb_id: int,
    body: KnowledgeBaseConfirmMode,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.confirm_mode(
        db,
        kb_id=kb_id,
        user_id=current_user.id,
        body=body,
        background_enqueue=lambda doc_id: background_tasks.add_task(
            svc.run_ingest_document, doc_id
        ),
    )


@router.get(
    "/{kb_id}/drill-status",
    response_model=DrillStatusPublic,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_drill_status(
    kb_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, switched = maybe_auto_downgrade_empty_drill(
        db,
        kb_id=kb_id,
        user_id=current_user.id,
        background_enqueue=lambda doc_id: background_tasks.add_task(
            svc.run_ingest_document, doc_id
        ),
    )
    return drill_service.get_drill_status(
        db,
        kb_id=kb_id,
        user_id=current_user.id,
        auto_switched=switched,
    )


@router.post(
    "/{kb_id}/reset-practice",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def reset_practice(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    drill_service.reset_practice(db, kb_id=kb_id, user_id=current_user.id)
    return {"ok": True}


@router.get(
    "/{kb_id}/master-status",
    response_model=MasterStatusPublic,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_master_status(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return master_map_service.get_master_status(
        db, kb_id=kb_id, user_id=current_user.id
    )


@router.post(
    "/{kb_id}/master-map/rebuild",
    response_model=MasterStatusPublic,
    responses={
        401: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def rebuild_master_map(
    kb_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return master_map_service.request_rebuild(
        db,
        kb_id=kb_id,
        user_id=current_user.id,
        background_enqueue=lambda doc_id: background_tasks.add_task(
            master_map_service.run_generate_master_map, doc_id
        ),
    )


@router.post(
    "/{kb_id}/reset-master-coverage",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def reset_master_coverage(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    master_map_service.reset_master_coverage(
        db, kb_id=kb_id, user_id=current_user.id
    )
    return {"ok": True}


@router.post(
    "/{kb_id}/questions/{question_id}/explanation",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def generate_question_explanation(
    kb_id: int,
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = drill_service.get_question_owned(
        db, kb_id=kb_id, question_id=question_id, user_id=current_user.id
    )
    text, source = ensure_ai_explanation(db, question=q)
    return {
        "question_id": q.id,
        "explanation": text,
        "explanation_source": source,
    }


@router.delete(
    "/{kb_id}",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def delete_knowledge_base(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc.delete_base(db, kb_id=kb_id, user_id=current_user.id)
    return {"ok": True}


@router.get(
    "/{kb_id}/documents",
    response_model=list[KnowledgeDocumentPublic],
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def list_documents(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.list_documents(db, kb_id=kb_id, user_id=current_user.id)


@router.post(
    "/{kb_id}/documents",
    response_model=KnowledgeDocumentPublic,
    responses={401: {"model": ErrorResponse}, 400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def upload_document(
    kb_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename = file.filename or "unnamed"
    raw = await file.read()
    if not raw:
        raise bad_request("VALIDATION_ERROR", "文件为空")
    doc = svc.create_pending_document(
        db,
        kb_id=kb_id,
        user_id=current_user.id,
        filename=filename,
        raw=raw,
    )
    background_tasks.add_task(svc.run_ingest_document, doc.id)
    return doc


@router.get(
    "/{kb_id}/documents/{doc_id}",
    response_model=KnowledgeDocumentPublic,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_document(
    kb_id: int,
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.get_document(db, kb_id=kb_id, doc_id=doc_id, user_id=current_user.id)


@router.delete(
    "/{kb_id}/documents/{doc_id}",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def delete_document(
    kb_id: int,
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc.delete_document(db, kb_id=kb_id, doc_id=doc_id, user_id=current_user.id)
    return {"ok": True}

"""Chroma helpers: one collection per knowledge base."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence
from uuid import uuid4

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.config import get_settings


def collection_name_for_kb(knowledge_base_id: int) -> str:
    return f"kb_{knowledge_base_id}"


def chunk_id(document_id: int, chunk_index: int) -> str:
    return f"doc{document_id}_c{chunk_index}"


def get_vector_store(
    knowledge_base_id: int,
    *,
    embeddings: Embeddings,
    persist_directory: str | None = None,
) -> Chroma:
    settings = get_settings()
    persist = persist_directory or settings.chroma_persist_dir
    Path(persist).mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=collection_name_for_kb(knowledge_base_id),
        embedding_function=embeddings,
        persist_directory=persist,
    )


def add_chunks(
    store: Chroma,
    *,
    texts: Sequence[str],
    user_id: int,
    knowledge_base_id: int,
    document_id: int,
    filename: str,
) -> list[str]:
    docs: list[Document] = []
    ids: list[str] = []
    for idx, text in enumerate(texts):
        cid = chunk_id(document_id, idx)
        ids.append(cid)
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "user_id": user_id,
                    "knowledge_base_id": knowledge_base_id,
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": idx,
                },
            )
        )
    if docs:
        store.add_documents(documents=docs, ids=ids)
    return ids


def _where_filter(
    *,
    knowledge_base_id: int,
    user_id: int | None = None,
) -> dict:
    """Chroma where filters allow one top-level key; combine with $and."""
    clauses: list[dict] = [{"knowledge_base_id": knowledge_base_id}]
    if user_id is not None:
        clauses.append({"user_id": user_id})
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def similarity_search(
    store: Chroma,
    query: str,
    *,
    knowledge_base_id: int,
    user_id: int | None = None,
    k: int = 6,
) -> list[Document]:
    return store.similarity_search(
        query,
        k=k,
        filter=_where_filter(knowledge_base_id=knowledge_base_id, user_id=user_id),
    )


def delete_document_chunks(store: Chroma, *, document_id: int, chunk_count: int) -> None:
    if chunk_count <= 0:
        return
    ids = [chunk_id(document_id, i) for i in range(chunk_count)]
    store.delete(ids=ids)


def delete_knowledge_base_collection(
    knowledge_base_id: int,
    *,
    embeddings: Embeddings,
    persist_directory: str | None = None,
) -> None:
    store = get_vector_store(
        knowledge_base_id,
        embeddings=embeddings,
        persist_directory=persist_directory,
    )
    store.delete_collection()


def new_ephemeral_ids(n: int) -> list[str]:
    return [str(uuid4()) for _ in range(n)]

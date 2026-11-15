"""LangChain tools for knowledge-base retrieval (Agentic RAG)."""

from __future__ import annotations

from typing import Any

from langchain.tools import tool
from sqlalchemy.orm import Session

from app.services import chroma_store
from app.services.embeddings import get_embeddings
from app.services.knowledge_service import list_ready_bases_summary
from app.services.tool_call_logging import preview_text

_MAX_RETRIEVE_CHARS = 8000


def format_docs(docs: list[Any]) -> str:
    parts: list[str] = []
    total = 0
    for i, doc in enumerate(docs, start=1):
        meta = getattr(doc, "metadata", {}) or {}
        header = f"[{i}] {meta.get('filename', 'doc')}#{meta.get('chunk_index', '?')}"
        body = (getattr(doc, "page_content", "") or "").strip()
        block = f"{header}\n{body}"
        if total + len(block) > _MAX_RETRIEVE_CHARS:
            remain = _MAX_RETRIEVE_CHARS - total
            if remain > 80:
                parts.append(block[:remain] + "…")
            break
        parts.append(block)
        total += len(block) + 2
    return "\n\n".join(parts).strip()


def retrieve_kb_context(
    *,
    knowledge_base_id: int,
    user_id: int,
    query: str,
    k: int = 6,
) -> str:
    emb = get_embeddings()
    store = chroma_store.get_vector_store(knowledge_base_id, embeddings=emb)
    docs = chroma_store.similarity_search(
        store,
        query,
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
        k=k,
    )
    return format_docs(docs)


def build_kb_tools(*, db: Session, user_id: int, forced_kb_id: int | None = None):
    """Build retrieve (and optional list) tools bound to the current user."""

    ready = list_ready_bases_summary(db, user_id)
    ready_ids = {item["id"] for item in ready}

    @tool
    def kb_list_ready() -> str:
        """列出当前用户已有就绪文档的知识库（id 与名称）。仅当主题可能对应私有资料时再检索。"""
        if not ready:
            return "当前没有含就绪文档的知识库。"
        lines = [f"- id={item['id']} name={item['name']} ready_docs={item['ready_document_count']}" for item in ready]
        return "就绪知识库：\n" + "\n".join(lines)

    @tool
    def kb_retrieve(knowledge_base_id: int, query: str) -> str:
        """在指定知识库内按语义检索私有资料片段。仅检索属于当前用户且已就绪的库；主题相关时再调用。"""
        q = (query or "").strip()
        if not q:
            return "查询为空，未检索。"
        if forced_kb_id is not None and knowledge_base_id != forced_kb_id:
            return f"当前为强制知识库模式，只能检索 knowledge_base_id={forced_kb_id}。"
        if knowledge_base_id not in ready_ids and forced_kb_id is None:
            return f"知识库 {knowledge_base_id} 不存在、不属于你，或没有就绪文档。"
        if forced_kb_id is not None and knowledge_base_id != forced_kb_id:
            return "越权或错误的知识库 id。"
        # ownership: only ready ids for this user (forced path also validated upstream)
        if knowledge_base_id not in ready_ids and forced_kb_id == knowledge_base_id:
            # force path may have just become ready; allow retrieve attempt
            pass
        elif knowledge_base_id not in ready_ids:
            return f"知识库 {knowledge_base_id} 不可用。"
        text = retrieve_kb_context(
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            query=q,
        )
        if not text:
            return f"知识库 {knowledge_base_id} 未检索到相关片段（query={preview_text(q, limit=40)}）。"
        return text

    if forced_kb_id is not None:

        @tool
        def kb_retrieve_forced(query: str) -> str:
            """在当前指定的知识库内检索材料片段，用于材料优先出题。可多次用不同 query 检索。"""
            return kb_retrieve.invoke(
                {"knowledge_base_id": forced_kb_id, "query": query}
            )

        return [kb_retrieve_forced]

    return [kb_list_ready, kb_retrieve]

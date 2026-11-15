"""Research / Agentic RAG step before structured quiz generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.kb_tools import build_kb_tools
from app.services.knowledge_service import user_has_ready_knowledge
from app.services.llm import get_quiz_llm
from app.services.prompts import (
    RESEARCH_HUMAN,
    RESEARCH_HUMAN_KB,
    RESEARCH_HUMAN_ROUTE,
    RESEARCH_SYSTEM,
    RESEARCH_SYSTEM_KB_ONLY,
    RESEARCH_SYSTEM_WITH_KB,
)
from app.services.tavily_tools import build_quiz_research_tools
from app.services.tool_call_logging import ResearchToolCallLogger, preview_text

logger = logging.getLogger(__name__)

_MAX_CONTEXT_CHARS = 12000


@dataclass
class ResearchResult:
    context: str | None
    used_knowledge_base: bool = False
    mode: str = "none"  # none | web | agentic | kb_forced


class KnowledgeBaseGroundingError(RuntimeError):
    """Forced KB mode could not gather material — must not silent-fallback."""


def _message_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                text = getattr(block, "text", None)
                if text:
                    parts.append(str(text))
        return "\n".join(p for p in parts if p).strip()
    return str(content).strip()


def _extract_final_text(result: dict[str, Any]) -> str:
    messages = result.get("messages") or []
    for msg in reversed(messages):
        type_name = getattr(msg, "type", None) or getattr(msg, "role", None)
        if type_name in {"ai", "assistant"}:
            text = _message_text(getattr(msg, "content", None))
            if text:
                return text
        if isinstance(msg, dict):
            role = msg.get("type") or msg.get("role")
            if role in {"ai", "assistant"}:
                text = _message_text(msg.get("content"))
                if text:
                    return text
    return ""


def _summarize_tool_calls(result: dict[str, Any]) -> list[str]:
    summary: list[str] = []
    for msg in result.get("messages") or []:
        type_name = getattr(msg, "type", None)
        if type_name == "tool":
            name = getattr(msg, "name", None) or "tool"
            summary.append(f"{name}(result)")
            continue
        tool_calls = getattr(msg, "tool_calls", None) or []
        for call in tool_calls:
            if isinstance(call, dict):
                name = call.get("name") or "tool"
                args = preview_text(call.get("args") or {}, limit=100)
            else:
                name = getattr(call, "name", None) or "tool"
                args = preview_text(getattr(call, "args", {}), limit=100)
            summary.append(f"{name}({args})")
    return summary


def _clip(text: str) -> str:
    if len(text) > _MAX_CONTEXT_CHARS:
        return text[:_MAX_CONTEXT_CHARS] + "\n…(已截断)"
    return text


def _run_agent(
    *,
    tools: list,
    system_prompt: str,
    human: str,
    clue: str,
) -> str | None:
    llm = get_quiz_llm()
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )
    result = agent.invoke(
        {"messages": [{"role": "user", "content": human}]},
        config={"callbacks": [ResearchToolCallLogger()]},
    )
    payload = result if isinstance(result, dict) else {}
    tool_summary = _summarize_tool_calls(payload)
    if tool_summary:
        logger.info(
            "quiz_grounding=tools_used count=%s calls=%s",
            len(tool_summary),
            tool_summary,
        )
    else:
        logger.warning(
            "quiz_grounding=no_tool_calls clue=%s",
            clue,
        )
    text = _extract_final_text(payload)
    if not text:
        return None
    if "未找到可用资料" in text and len(text) < 80:
        return None
    return _clip(text)


def gather_research_context(
    source_text: str,
    *,
    db: Session | None = None,
    user_id: int | None = None,
    knowledge_base_id: int | None = None,
) -> ResearchResult:
    """
    Gather grounding context.

    - knowledge_base_id set: forced KB only; empty => raise KnowledgeBaseGroundingError
    - else if user has ready KB: agentic tools (Tavily + KB) when Tavily key present;
      if no Tavily, still allow KB-only agentic
    - else: Tavily web only (legacy); failures => empty context for silent model fallback
    """
    settings = get_settings()
    clue = preview_text(source_text, limit=80)

    # ----- Forced KB mode -----
    if knowledge_base_id is not None:
        if db is None or user_id is None:
            raise KnowledgeBaseGroundingError("强制知识库模式缺少用户上下文")
        logger.info(
            "quiz_grounding=start mode=kb_forced kb_id=%s clue=%s",
            knowledge_base_id,
            clue,
        )
        try:
            tools = build_kb_tools(db=db, user_id=user_id, forced_kb_id=knowledge_base_id)
            text = _run_agent(
                tools=tools,
                system_prompt=RESEARCH_SYSTEM_KB_ONLY,
                human=RESEARCH_HUMAN_KB.format(source_text=source_text),
                clue=clue,
            )
        except Exception as exc:  # noqa: BLE001
            raise KnowledgeBaseGroundingError(f"知识库检索失败：{exc}") from exc
        if not text:
            raise KnowledgeBaseGroundingError("知识库未检索到足够材料，无法按材料出题")
        logger.info(
            "quiz_grounding=ok mode=kb_forced context_chars=%s",
            len(text),
        )
        return ResearchResult(context=text, used_knowledge_base=True, mode="kb_forced")

    has_kb = bool(db is not None and user_id is not None and user_has_ready_knowledge(db, user_id))
    tavily_ok = bool(settings.quiz_web_grounding and settings.tavily_api_key)

    # ----- Agentic: ready KB + optional web -----
    if has_kb and db is not None and user_id is not None:
        logger.info(
            "quiz_grounding=start mode=agentic has_tavily=%s clue=%s",
            tavily_ok,
            clue,
        )
        try:
            tools = build_kb_tools(db=db, user_id=user_id, forced_kb_id=None)
            if tavily_ok:
                tools = build_quiz_research_tools(api_key=settings.tavily_api_key) + tools
                system = RESEARCH_SYSTEM_WITH_KB
            else:
                system = RESEARCH_SYSTEM_KB_ONLY
            text = _run_agent(
                tools=tools,
                system_prompt=system,
                human=RESEARCH_HUMAN_ROUTE.format(source_text=source_text),
                clue=clue,
            )
            if text:
                logger.info("quiz_grounding=ok mode=agentic context_chars=%s", len(text))
                return ResearchResult(context=text, used_knowledge_base=True, mode="agentic")
        except Exception as exc:  # noqa: BLE001
            logger.info(
                "quiz_grounding=degraded mode=agentic err=%s clue=%s",
                preview_text(exc, limit=120),
                clue,
            )
        # fall through to web-only or none

    # ----- Web only (no ready KB, or agentic failed) -----
    if not tavily_ok:
        if not settings.quiz_web_grounding:
            logger.info("quiz_grounding=skipped reason=disabled clue=%s", clue)
        else:
            logger.info("quiz_grounding=degraded reason=missing_tavily_key clue=%s", clue)
        return ResearchResult(context=None, used_knowledge_base=False, mode="none")

    logger.info(
        "quiz_grounding=start mode=web tools=%s clue=%s",
        ["tavily_search", "tavily_search_china", "tavily_extract"],
        clue,
    )
    try:
        tools = build_quiz_research_tools(api_key=settings.tavily_api_key)
        text = _run_agent(
            tools=tools,
            system_prompt=RESEARCH_SYSTEM,
            human=RESEARCH_HUMAN.format(source_text=source_text),
            clue=clue,
        )
        if not text:
            logger.info("quiz_grounding=degraded reason=empty_research clue=%s", clue)
            return ResearchResult(context=None, used_knowledge_base=False, mode="web")
        logger.info("quiz_grounding=ok mode=web context_chars=%s", len(text))
        return ResearchResult(context=text, used_knowledge_base=False, mode="web")
    except Exception as exc:  # noqa: BLE001
        logger.info(
            "quiz_grounding=degraded reason=research_error err_type=%s err=%s clue=%s",
            type(exc).__name__,
            preview_text(exc, limit=120),
            clue,
        )
        return ResearchResult(context=None, used_knowledge_base=False, mode="web")

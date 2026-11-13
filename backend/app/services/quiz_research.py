"""Web research step before structured quiz generation (two-phase grounding)."""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents import create_agent

from app.config import get_settings
from app.services.llm import get_quiz_llm
from app.services.prompts import RESEARCH_HUMAN, RESEARCH_SYSTEM
from app.services.tavily_tools import build_quiz_research_tools
from app.services.tool_call_logging import ResearchToolCallLogger, preview_text

logger = logging.getLogger(__name__)

_MAX_CONTEXT_CHARS = 12000


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
    """Collect tool names (and brief args) from the agent transcript."""
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


def gather_research_context(source_text: str) -> str | None:
    """
    Run a tool-using research agent and return condensed external context.

    Returns None on missing key / tool / agent failure / empty output so the
    caller can silently fall back to model-only quiz generation.
    """
    settings = get_settings()
    clue = preview_text(source_text, limit=80)
    if not settings.quiz_web_grounding:
        logger.info("quiz_grounding=skipped reason=disabled clue=%s", clue)
        return None
    if not settings.tavily_api_key:
        logger.info("quiz_grounding=degraded reason=missing_tavily_key clue=%s", clue)
        return None

    logger.info(
        "quiz_grounding=start clue=%s tools=%s",
        clue,
        ["tavily_search", "tavily_search_china", "tavily_extract"],
    )

    try:
        tools = build_quiz_research_tools(api_key=settings.tavily_api_key)
        llm = get_quiz_llm()
        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=RESEARCH_SYSTEM,
        )
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": RESEARCH_HUMAN.format(source_text=source_text),
                    }
                ]
            },
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
                "quiz_grounding=no_tool_calls clue=%s "
                "(agent finished without calling Tavily)",
                clue,
            )

        text = _extract_final_text(payload)
        if not text:
            logger.info("quiz_grounding=degraded reason=empty_research clue=%s", clue)
            return None
        if len(text) > _MAX_CONTEXT_CHARS:
            text = text[:_MAX_CONTEXT_CHARS] + "\n…(已截断)"
        logger.info(
            "quiz_grounding=ok context_chars=%s preview=%s",
            len(text),
            preview_text(text, limit=120),
        )
        return text
    except Exception as exc:  # noqa: BLE001 - silent degrade path
        logger.info(
            "quiz_grounding=degraded reason=research_error err_type=%s err=%s clue=%s",
            type(exc).__name__,
            preview_text(exc, limit=120),
            clue,
        )
        return None

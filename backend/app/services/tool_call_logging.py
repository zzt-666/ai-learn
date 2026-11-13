"""LangChain callback: log each tool call so Tavily usage is visible in console."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger("app.services.quiz_research")

_PREVIEW_LEN = 160


def preview_text(value: Any, limit: int = _PREVIEW_LEN) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            text = json.dumps(value, ensure_ascii=False)
        except TypeError:
            text = str(value)
    else:
        text = str(value)
    text = " ".join(text.split())
    if len(text) > limit:
        return text[:limit] + "…"
    return text


class ResearchToolCallLogger(BaseCallbackHandler):
    """Prints when the research agent starts/ends each Tavily (or other) tool."""

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        name = (
            (serialized or {}).get("name")
            or (metadata or {}).get("name")
            or "unknown_tool"
        )
        detail = preview_text(inputs if inputs is not None else input_str)
        logger.info("tavily_tool_start name=%s input=%s", name, detail)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        text = preview_text(getattr(output, "content", output), limit=200)
        # Prefer tool name from kwargs if present
        name = kwargs.get("name") or "tool"
        logger.info("tavily_tool_end name=%s output_preview=%s", name, text)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        name = kwargs.get("name") or "tool"
        logger.warning(
            "tavily_tool_error name=%s err_type=%s err=%s",
            name,
            type(error).__name__,
            preview_text(error, limit=120),
        )

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.quiz_research import (
    KnowledgeBaseGroundingError,
    ResearchResult,
    gather_research_context,
)


def test_no_kb_uses_web_or_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.quiz_research.user_has_ready_knowledge",
        lambda db, user_id: False,
    )
    monkeypatch.setattr(
        "app.services.quiz_research.get_settings",
        lambda: SimpleNamespace(quiz_web_grounding=True, tavily_api_key=""),
    )
    result = gather_research_context("光合作用", db=MagicMock(), user_id=1)
    assert isinstance(result, ResearchResult)
    assert result.context is None
    assert result.mode == "none"


def test_forced_kb_empty_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.quiz_research.build_kb_tools",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        "app.services.quiz_research._run_agent",
        lambda **kwargs: None,
    )
    with pytest.raises(KnowledgeBaseGroundingError):
        gather_research_context(
            "根据本库出题",
            db=MagicMock(),
            user_id=1,
            knowledge_base_id=9,
        )


def test_agentic_path_when_user_has_kb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.quiz_research.user_has_ready_knowledge",
        lambda db, user_id: True,
    )
    monkeypatch.setattr(
        "app.services.quiz_research.get_settings",
        lambda: SimpleNamespace(quiz_web_grounding=False, tavily_api_key=""),
    )
    monkeypatch.setattr(
        "app.services.quiz_research.build_kb_tools",
        lambda **kwargs: [object()],
    )
    monkeypatch.setattr(
        "app.services.quiz_research._run_agent",
        lambda **kwargs: "知识库材料摘要：退货 7 日",
    )
    result = gather_research_context("客服退货政策", db=MagicMock(), user_id=1)
    assert result.context and "退货" in result.context
    assert result.used_knowledge_base is True
    assert result.mode == "agentic"

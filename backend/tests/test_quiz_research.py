from unittest.mock import MagicMock, patch

from app.services.quiz_research import gather_research_context


def test_gather_research_missing_key_returns_none(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("QUIZ_WEB_GROUNDING", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        assert gather_research_context("Harness Engineering") is None
    finally:
        get_settings.cache_clear()


def test_gather_research_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("QUIZ_WEB_GROUNDING", "false")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        assert gather_research_context("主题") is None
    finally:
        get_settings.cache_clear()


def test_gather_research_agent_error_returns_none(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("QUIZ_WEB_GROUNDING", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        with (
            patch(
                "app.services.quiz_research.build_quiz_research_tools",
                return_value=[MagicMock()],
            ),
            patch("app.services.quiz_research.get_quiz_llm", return_value=MagicMock()),
            patch(
                "app.services.quiz_research.create_agent",
                side_effect=RuntimeError("agent boom"),
            ),
        ):
            assert gather_research_context("主题") is None
    finally:
        get_settings.cache_clear()


def test_gather_research_success_returns_text(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("QUIZ_WEB_GROUNDING", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    agent = MagicMock()
    ai_msg = MagicMock()
    ai_msg.type = "ai"
    ai_msg.content = "调研摘要：Harness Engineering 是…。"
    agent.invoke.return_value = {"messages": [ai_msg]}

    try:
        with (
            patch(
                "app.services.quiz_research.build_quiz_research_tools",
                return_value=[MagicMock()],
            ),
            patch("app.services.quiz_research.get_quiz_llm", return_value=MagicMock()),
            patch("app.services.quiz_research.create_agent", return_value=agent),
        ):
            text = gather_research_context("Harness Engineering")
        assert text is not None
        assert "Harness" in text
        agent.invoke.assert_called_once()
    finally:
        get_settings.cache_clear()

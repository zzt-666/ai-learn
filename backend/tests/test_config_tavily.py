from app.config import Settings


def test_settings_reads_tavily_fields(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    monkeypatch.setenv("QUIZ_AGENT_TIMEOUT_SECONDS", "150")
    monkeypatch.setenv("QUIZ_WEB_GROUNDING", "false")

    settings = Settings()

    assert settings.tavily_api_key == "tvly-test-key"
    assert settings.quiz_agent_timeout_seconds == 150
    assert settings.quiz_web_grounding is False


def test_settings_tavily_defaults(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("QUIZ_AGENT_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("QUIZ_WEB_GROUNDING", raising=False)

    settings = Settings()

    assert settings.tavily_api_key == ""
    assert settings.quiz_agent_timeout_seconds == 120
    assert settings.quiz_web_grounding is True

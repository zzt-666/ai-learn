from functools import lru_cache

from langchain_deepseek import ChatDeepSeek

from app.config import get_settings


@lru_cache
def get_quiz_llm() -> ChatDeepSeek:
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY，无法调用模型")
    return ChatDeepSeek(
        model=settings.deepseek_model,
        temperature=0.3,
        max_retries=2,
        timeout=settings.quiz_timeout_seconds,
        api_key=settings.deepseek_api_key,
    )


@lru_cache
def get_report_llm() -> ChatDeepSeek:
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY，无法调用模型")
    return ChatDeepSeek(
        model=settings.deepseek_model,
        temperature=0.4,
        max_retries=2,
        timeout=settings.report_timeout_seconds,
        api_key=settings.deepseek_api_key,
    )

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
        self.quiz_timeout_seconds: int = int(os.getenv("QUIZ_TIMEOUT_SECONDS", "90"))
        self.report_timeout_seconds: int = int(os.getenv("REPORT_TIMEOUT_SECONDS", "90"))
        self.source_excerpt_max_chars: int = int(os.getenv("SOURCE_EXCERPT_MAX_CHARS", "2000"))


@lru_cache
def get_settings() -> Settings:
    return Settings()

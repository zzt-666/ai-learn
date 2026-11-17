import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
        self.quiz_timeout_seconds: int = int(os.getenv("QUIZ_TIMEOUT_SECONDS", "90"))
        self.report_timeout_seconds: int = int(os.getenv("REPORT_TIMEOUT_SECONDS", "90"))
        self.source_excerpt_max_chars: int = int(os.getenv("SOURCE_EXCERPT_MAX_CHARS", "2000"))

        self.tavily_api_key: str = os.getenv("TAVILY_API_KEY", "").strip()
        self.quiz_agent_timeout_seconds: int = int(
            os.getenv("QUIZ_AGENT_TIMEOUT_SECONDS", "120")
        )
        self.quiz_web_grounding: bool = _as_bool(
            os.getenv("QUIZ_WEB_GROUNDING"), default=True
        )

        self.wechat_app_id: str = os.getenv("WECHAT_APP_ID", "").strip()
        self.wechat_app_secret: str = os.getenv("WECHAT_APP_SECRET", "").strip()
        self.wechat_mock_login: bool = _as_bool(os.getenv("WECHAT_MOCK_LOGIN"), default=True)

        self.jwt_secret: str = os.getenv("JWT_SECRET", "dev-insecure-jwt-secret-change-me").strip()
        self.jwt_expire_days: int = int(os.getenv("JWT_EXPIRE_DAYS", "7"))

        self.mysql_host: str = os.getenv("MYSQL_HOST", "127.0.0.1").strip()
        self.mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
        self.mysql_user: str = os.getenv("MYSQL_USER", "root").strip()
        self.mysql_password: str = os.getenv("MYSQL_PASSWORD", "").strip()
        self.mysql_database: str = os.getenv("MYSQL_DATABASE", "ai_learn").strip()

        self.upload_dir: str = os.getenv("UPLOAD_DIR", "uploads").strip() or "uploads"

        self.dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "").strip()
        self.dashscope_embedding_model: str = (
            os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4").strip()
            or "text-embedding-v4"
        )
        self.dashscope_embedding_dimensions: int = int(
            os.getenv("DASHSCOPE_EMBEDDING_DIMENSIONS", "1024")
        )
        self.dashscope_embedding_base_url: str = (
            os.getenv(
                "DASHSCOPE_EMBEDDING_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ).strip()
            or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.chroma_persist_dir: str = (
            os.getenv("CHROMA_PERSIST_DIR", "chroma_data").strip() or "chroma_data"
        )
        self.kb_max_file_bytes: int = int(os.getenv("KB_MAX_FILE_BYTES", str(10 * 1024 * 1024)))
        # Product rule: one document per knowledge base (re-upload replaces).
        self.kb_max_docs_per_base: int = int(os.getenv("KB_MAX_DOCS_PER_BASE", "1"))
        self.kb_max_bases_per_user: int = int(os.getenv("KB_MAX_BASES_PER_USER", "10"))

        self.oss_access_key_id: str = os.getenv("OSS_ACCESS_KEY_ID", "").strip()
        self.oss_access_key_secret: str = os.getenv("OSS_ACCESS_KEY_SECRET", "").strip()
        self.oss_bucket: str = os.getenv("OSS_BUCKET", "").strip()
        self.oss_endpoint: str = os.getenv("OSS_ENDPOINT", "").strip()
        self.oss_region: str = os.getenv("OSS_REGION", "").strip()

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            "?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

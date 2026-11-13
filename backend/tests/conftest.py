"""
Pytest fixtures.

IMPORTANT: tests MUST use a dedicated database (ai_learn_test by default),
never the developer/production MYSQL_DATABASE from .env. An earlier version
connected to the same engine as the app and DELETE'd all rows after each test,
which wiped local learning history.
"""

from __future__ import annotations

import os

# Force test DB + mock login before app settings / engine are imported.
os.environ["WECHAT_MOCK_LOGIN"] = "true"
os.environ["MYSQL_DATABASE"] = os.environ.get("MYSQL_TEST_DATABASE", "ai_learn_test")
if not os.getenv("JWT_SECRET"):
    os.environ["JWT_SECRET"] = "test-secret-at-least-32-characters!!"

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

get_settings.cache_clear()
settings = get_settings()

_FORBIDDEN = {"ai_learn"}
if settings.mysql_database in _FORBIDDEN and not os.environ.get(
    "PYTEST_ALLOW_PRIMARY_DB"
):
    raise RuntimeError(
        f"Refusing to run pytest against MYSQL_DATABASE={settings.mysql_database!r}. "
        "Tests must use ai_learn_test (set automatically in conftest). "
        "If you really intend to use the primary DB, set PYTEST_ALLOW_PRIMARY_DB=1."
    )


def _ensure_database_exists() -> None:
    root_url = (
        f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/?charset=utf8mb4"
    )
    root_engine = create_engine(root_url)
    with root_engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{settings.mysql_database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
    root_engine.dispose()


_ensure_database_exists()

import app.db.base as db_base  # noqa: E402
from app.db.base import Base, get_db  # noqa: E402
from app.db import models  # noqa: F401, E402
from app.main import app  # noqa: E402

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Background workers import SessionLocal from app.db.base — point them at the test DB.
db_base.engine = engine
db_base.SessionLocal = TestingSessionLocal


@pytest.fixture(scope="session", autouse=True)
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def clean_tables() -> Generator[None, None, None]:
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"DELETE FROM `{table.name}`"))


@pytest.fixture
def db_session() -> Generator:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    resp = client.post("/api/v1/auth/wechat/login", json={"code": "pytest_user_a"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(client: TestClient) -> dict[str, str]:
    resp = client.post("/api/v1/auth/wechat/login", json={"code": "pytest_user_b"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

import os

# 测试强制 Mock 登录，避免依赖真实微信
os.environ["WECHAT_MOCK_LOGIN"] = "true"
if not os.getenv("JWT_SECRET"):
    os.environ["JWT_SECRET"] = "test-secret-at-least-32-characters!!"

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.db.base import Base, SessionLocal, engine, get_db
from app.db import models  # noqa: F401  ensure models registered
from app.main import app

get_settings.cache_clear()


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
    db = SessionLocal()
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

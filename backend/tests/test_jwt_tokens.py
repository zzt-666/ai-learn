import time

import pytest

from app.services.jwt_tokens import create_access_token, decode_access_token


def test_create_and_decode_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-at-least-32-characters!!")
    monkeypatch.setenv("JWT_EXPIRE_DAYS", "7")
    from app.config import get_settings

    get_settings.cache_clear()

    token = create_access_token(user_id=42)
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert "exp" in payload

    get_settings.cache_clear()


def test_decode_invalid_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-at-least-32-characters!!")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValueError):
        decode_access_token("not.a.jwt")
    get_settings.cache_clear()


def test_expired_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-at-least-32-characters!!")
    monkeypatch.setenv("JWT_EXPIRE_DAYS", "0")
    from app.config import get_settings

    get_settings.cache_clear()
    token = create_access_token(user_id=1, expire_seconds=-1)
    time.sleep(0.05)
    with pytest.raises(ValueError):
        decode_access_token(token)
    get_settings.cache_clear()

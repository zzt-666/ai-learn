"""Unit tests for object storage abstraction."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.services import object_storage as os_mod
from app.services.object_storage import (
    LocalObjectStorage,
    OssObjectStorage,
    avatar_key_from_url,
    get_object_storage,
    is_oss_configured,
    override_object_storage,
)


def _settings(**overrides) -> Settings:
    s = Settings.__new__(Settings)
    s.upload_dir = "uploads"
    s.oss_access_key_id = ""
    s.oss_access_key_secret = ""
    s.oss_bucket = ""
    s.oss_endpoint = ""
    s.oss_region = ""
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def test_is_oss_configured_requires_all_fields():
    base = dict(
        oss_access_key_id="id",
        oss_access_key_secret="secret",
        oss_bucket="zzt-wwcg",
        oss_endpoint="https://oss-cn-hangzhou.aliyuncs.com",
        oss_region="cn-hangzhou",
    )
    assert is_oss_configured(_settings(**base)) is True
    assert is_oss_configured(_settings(**{**base, "oss_access_key_id": ""})) is False
    assert is_oss_configured(_settings(**{**base, "oss_access_key_secret": ""})) is False
    assert is_oss_configured(_settings(**{**base, "oss_bucket": ""})) is False
    assert (
        is_oss_configured(
            _settings(**{**base, "oss_endpoint": "", "oss_region": ""})
        )
        is False
    )
    assert (
        is_oss_configured(
            _settings(**{**base, "oss_endpoint": "", "oss_region": "cn-hangzhou"})
        )
        is True
    )


def test_local_put_get_delete(tmp_path: Path):
    store = LocalObjectStorage(tmp_path)
    key = "knowledge/1/2/3_a.md"
    store.put(key, b"hello", content_type="text/markdown")
    assert store.get(key) == b"hello"
    assert store.public_url(key) == "/uploads/knowledge/1/2/3_a.md"
    store.delete(key)
    assert not (tmp_path / "knowledge" / "1" / "2" / "3_a.md").exists()
    store.delete(key)  # missing is ok


def test_factory_local_when_incomplete(monkeypatch):
    override_object_storage(None)
    s = _settings(upload_dir="uploads_test_local")
    monkeypatch.setattr(os_mod, "get_settings", lambda: s)
    store = get_object_storage(s)
    assert isinstance(store, LocalObjectStorage)


def test_factory_oss_when_configured(monkeypatch):
    override_object_storage(None)
    s = _settings(
        oss_access_key_id="id",
        oss_access_key_secret="secret",
        oss_bucket="zzt-wwcg",
        oss_endpoint="https://oss-cn-hangzhou.aliyuncs.com",
        oss_region="cn-hangzhou",
    )
    sentinel = object()

    def _fake_oss(**_kwargs):
        return sentinel

    monkeypatch.setattr(os_mod, "OssObjectStorage", _fake_oss)
    store = get_object_storage(s)
    assert store is sentinel


def test_oss_put_get_delete_calls_client():
    client = MagicMock()
    body = MagicMock()
    body.__enter__ = MagicMock(return_value=body)
    body.__exit__ = MagicMock(return_value=False)
    body.read = MagicMock(return_value=b"data")
    client.get_object.return_value = MagicMock(body=body)

    store = OssObjectStorage(
        bucket="zzt-wwcg",
        access_key_id="id",
        access_key_secret="secret",
        region="cn-hangzhou",
        endpoint="https://oss-cn-hangzhou.aliyuncs.com",
        client=client,
    )
    store.put("avatars/a.png", b"img", content_type="image/png")
    assert client.put_object.called
    assert store.get("avatars/a.png") == b"data"
    store.delete("avatars/a.png")
    assert client.delete_object.called


def test_avatar_key_from_url():
    assert avatar_key_from_url("/uploads/avatars/1_x.png") == "avatars/1_x.png"
    assert (
        avatar_key_from_url(
            "https://zzt-wwcg.oss-cn-hangzhou.aliyuncs.com/avatars/1_x.png"
        )
        == "avatars/1_x.png"
    )
    assert avatar_key_from_url(None) is None
    assert avatar_key_from_url("https://example.com/other.png") is None


@pytest.fixture(autouse=True)
def _clear_storage_override():
    yield
    override_object_storage(None)

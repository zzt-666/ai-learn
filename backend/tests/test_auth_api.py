def test_wechat_mock_login_creates_user(client):
    resp = client.post("/api/v1/auth/wechat/login", json={"code": "abc123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["nickname"] == "阿衰同学"
    assert data["user"]["level"] == 1
    assert data["user"]["exp"] == 0
    assert data["user"]["points"] == 0
    assert data["user"]["completed_count"] == 0


def test_wechat_login_same_code_same_user(client):
    first = client.post("/api/v1/auth/wechat/login", json={"code": "same"}).json()
    second = client.post("/api/v1/auth/wechat/login", json={"code": "same"}).json()
    assert first["user"]["id"] == second["user"]["id"]


def test_me_requires_auth(client):
    resp = client.get("/api/v1/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error_code"] == "UNAUTHORIZED"


def test_me_with_token(client, auth_headers):
    resp = client.get("/api/v1/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "阿衰同学"


def test_quiz_requires_auth(client):
    resp = client.post(
        "/api/v1/quiz/generate",
        json={"source_text": "光合作用"},
    )
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "UNAUTHORIZED"


def test_update_nickname(client, auth_headers):
    resp = client.patch(
        "/api/v1/me",
        headers=auth_headers,
        json={"nickname": "  衰神  "},
    )
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "衰神"

    again = client.get("/api/v1/me", headers=auth_headers)
    assert again.json()["nickname"] == "衰神"


def test_update_nickname_empty_rejected(client, auth_headers):
    resp = client.patch(
        "/api/v1/me",
        headers=auth_headers,
        json={"nickname": "   "},
    )
    assert resp.status_code == 422


def test_avatar_rejects_non_image(client, auth_headers):
    resp = client.post(
        "/api/v1/me/avatar",
        headers=auth_headers,
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "INVALID_AVATAR"


def test_avatar_upload_ok(client, auth_headers):
    # 1x1 PNG
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    resp = client.post(
        "/api/v1/me/avatar",
        headers=auth_headers,
        files={"file": ("a.png", png, "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["avatar_url"].startswith("/uploads/avatars/")

from datetime import timedelta

import jwt
import pytest

from app import security
from app.extensions import db
from app.models import User

from .conftest import ANDROID_CLIENT_ID, TEST_SECRET, WEB_CLIENT_ID, make_app


def google_claims(**overrides):
    claims = {
        "iss": "https://accounts.google.com",
        "aud": ANDROID_CLIENT_ID,
        "sub": "google-sub-123",
        "email": "ana@gmail.com",
        "email_verified": True,
        "name": "Ana Souza",
        "picture": "https://lh3.googleusercontent.com/a/ana",
    }
    claims.update(overrides)
    return claims


@pytest.fixture
def fake_google(monkeypatch):
    state = {"claims": google_claims(), "calls": []}

    def fake_verify(token, audiences):
        state["calls"].append((token, audiences))
        if token == "invalid":
            raise ValueError("Token used too late")
        return state["claims"]

    monkeypatch.setattr(security, "verify_google_id_token", fake_verify)
    return state


def test_config(client):
    r = client.get("/api/v1/config")
    assert r.status_code == 200
    body = r.get_json()
    assert body["google_web_client_id"] == WEB_CLIENT_ID
    assert len(body["categories"]) == 17
    assert "cinema" in body["icon_keys"]
    assert body["invite_ttl_minutes"] == 60


@pytest.mark.parametrize("path", ["/health", "/api/v1/health"])
def test_health(client, path):
    assert client.get(path).get_json() == {"status": "ok"}


def test_google_login_creates_user(client, fake_google):
    r = client.post("/api/v1/auth/google", json={"id_token": "tok"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["user"]["email"] == "ana@gmail.com"
    assert body["user"]["display_name"] == "Ana Souza"
    assert body["user"]["avatar_url"].startswith("https://")
    assert body["access_token"] and body["refresh_token"]
    # verifica contra todos os client ids aceitos
    assert fake_google["calls"][0] == ("tok", [WEB_CLIENT_ID, ANDROID_CLIENT_ID])

    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.get_json() == body["user"]


def test_google_login_upserts_by_sub(app, client, fake_google):
    first = client.post("/api/v1/auth/google", json={"id_token": "tok"}).get_json()
    fake_google["claims"] = google_claims(name="Ana S.", email="ana.nova@gmail.com", picture=None)
    second = client.post("/api/v1/auth/google", json={"id_token": "tok"}).get_json()
    assert first["user"]["id"] == second["user"]["id"]
    assert second["user"]["display_name"] == "Ana S."
    assert second["user"]["email"] == "ana.nova@gmail.com"
    assert second["user"]["avatar_url"] is None
    with app.app_context():
        assert db.session.query(User).count() == 1


@pytest.mark.parametrize(
    "claims",
    [
        google_claims(email_verified=False),
        google_claims(email_verified=None),
        google_claims(iss="https://evil.example.com"),
        google_claims(aud="outro-client-id"),
        google_claims(email=None),
        google_claims(sub=None),
    ],
)
def test_google_login_rejects_bad_claims(client, fake_google, claims):
    fake_google["claims"] = claims
    r = client.post("/api/v1/auth/google", json={"id_token": "tok"})
    assert r.status_code == 401
    assert r.get_json()["error"]["code"] == "unauthorized"


def test_google_login_invalid_token(client, fake_google):
    r = client.post("/api/v1/auth/google", json={"id_token": "invalid"})
    assert r.status_code == 401
    assert "Token used too late" not in r.get_data(as_text=True)


@pytest.mark.parametrize("body", [{}, {"id_token": ""}, {"id_token": 123}])
def test_google_login_requires_token(client, fake_google, body):
    r = client.post("/api/v1/auth/google", json=body)
    assert r.status_code == 400


def test_dev_login_disabled_returns_404():
    app = make_app(DEV_LOGIN_ENABLED=False)
    r = app.test_client().post("/api/v1/auth/dev", json={"email": "a@b.com", "display_name": "A"})
    assert r.status_code == 404
    assert r.get_json()["error"]["code"] == "not_found"


def test_refresh_flow(client):
    tokens = client.post("/api/v1/auth/dev", json={"email": "r@x.com", "display_name": "R"}).get_json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    new = r.get_json()
    assert new["user"]["id"] == tokens["user"]["id"]
    assert new["refresh_token"] != tokens["refresh_token"]  # rotação
    assert new["access_token"] != tokens["access_token"]
    assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {new['access_token']}"}).status_code == 200


def test_refresh_rejects_access_token(client):
    tokens = client.post("/api/v1/auth/dev", json={"email": "r@x.com", "display_name": "R"}).get_json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401
    assert r.get_json()["error"]["code"] == "unauthorized"


def _forge(app, user_id, token_type, **delta):
    from app.timeutil import utcnow

    now = utcnow()
    payload = {
        "iss": app.config["JWT_ISSUER"],
        "aud": app.config["JWT_AUDIENCE"],
        "sub": user_id,
        "type": token_type,
        "iat": now - timedelta(hours=2),
        "exp": now + timedelta(**delta),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


def test_expired_access_token_returns_token_expired(app, client):
    tokens = client.post("/api/v1/auth/dev", json={"email": "e@x.com", "display_name": "E"}).get_json()
    expired = _forge(app, tokens["user"]["id"], "access", minutes=-1)
    r = client.get("/api/v1/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401
    assert r.get_json()["error"]["code"] == "token_expired"


def test_expired_refresh_token_is_unauthorized(app, client):
    tokens = client.post("/api/v1/auth/dev", json={"email": "e@x.com", "display_name": "E"}).get_json()
    expired = _forge(app, tokens["user"]["id"], "refresh", minutes=-1)
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": expired})
    assert r.status_code == 401
    assert r.get_json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize("header", [None, "", "Bearer", "Bearer ", "Basic abc", "Token xyz", "Bearer a.b.c"])
def test_missing_or_bad_authorization(client, header):
    headers = {"Authorization": header} if header is not None else {}
    r = client.get("/api/v1/workspaces", headers=headers)
    assert r.status_code == 401
    assert r.get_json()["error"]["code"] == "unauthorized"


def test_login_rate_limited(fake_google):
    from app.extensions import limiter

    app = make_app(RATELIMIT_ENABLED=True)
    limiter.reset()
    c = app.test_client()
    statuses = [c.post("/api/v1/auth/google", json={"id_token": "tok"}).status_code for _ in range(21)]
    assert statuses[:20] == [200] * 20
    assert statuses[20] == 429
    r = c.post("/api/v1/auth/google", json={"id_token": "tok"})
    assert r.get_json()["error"]["code"] == "rate_limited"
    limiter.reset()

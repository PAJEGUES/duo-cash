import itertools
from datetime import timedelta

import pytest

from app import create_app
from app.extensions import db
from app.timeutil import today

WEB_CLIENT_ID = "web-client.apps.googleusercontent.com"
ANDROID_CLIENT_ID = "android-client.apps.googleusercontent.com"
TEST_SECRET = "test-secret-key-with-at-least-32-characters!"

_counter = itertools.count(1)


def make_app(**overrides):
    config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": TEST_SECRET,
        "GOOGLE_CLIENT_IDS": [WEB_CLIENT_ID, ANDROID_CLIENT_ID],
        "PUBLIC_BASE_URL": "https://duocash.example.com",
        "DEV_LOGIN_ENABLED": True,
        "RATELIMIT_ENABLED": False,
        "INVITE_TTL_MINUTES": 60,
    }
    config.update(overrides)
    app = create_app(config)
    with app.app_context():
        db.create_all()
    return app


@pytest.fixture
def app():
    app = make_app()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


class Api:
    """Pequeno cliente para os testes: guarda o token de um usuário."""

    def __init__(self, client, tokens: dict):
        self.client = client
        self.tokens = tokens
        self.user = tokens["user"]
        self.id = self.user["id"]

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.tokens['access_token']}"}

    def _call(self, method, url, json=None, headers=None, **kw):
        h = dict(self.headers)
        h.update(headers or {})
        return getattr(self.client, method)(url, json=json, headers=h, **kw)

    def get(self, url, **kw):
        return self._call("get", url, **kw)

    def post(self, url, json=None, **kw):
        return self._call("post", url, json=json, **kw)

    def patch(self, url, json=None, **kw):
        return self._call("patch", url, json=json, **kw)

    def delete(self, url, **kw):
        return self._call("delete", url, **kw)

    # atalhos -----------------------------------------------------------
    def create_workspace(self, name="Casa", **extra):
        r = self.post("/api/v1/workspaces", json={"name": name, **extra})
        assert r.status_code == 201, r.get_json()
        return r.get_json()

    def create_expense(self, ws_id, expect=201, headers=None, **fields):
        body = expense_body(**fields)
        r = self.post(f"/api/v1/workspaces/{ws_id}/expenses", json=body, headers=headers)
        assert r.status_code == expect, r.get_json()
        return r.get_json()

    def invite(self, ws_id, role="EDITOR"):
        r = self.post(f"/api/v1/workspaces/{ws_id}/invites", json={"role": role})
        assert r.status_code == 201, r.get_json()
        return r.get_json()


def expense_body(**fields):
    body = {
        "amount_cents": 1000,
        "spent_at": today().isoformat(),
        "description": "Mercado",
        "category": "ALIMENTACAO",
    }
    body.update(fields)
    return body


def login(client, name=None, email=None) -> Api:
    n = next(_counter)
    name = name or f"Pessoa {n}"
    email = email or f"pessoa{n}@example.com"
    r = client.post("/api/v1/auth/dev", json={"email": email, "display_name": name})
    assert r.status_code == 200, r.get_json()
    return Api(client, r.get_json())


@pytest.fixture
def owner(client):
    return login(client, "Ana")


@pytest.fixture
def partner(client):
    return login(client, "Bruno")


@pytest.fixture
def stranger(client):
    return login(client, "Intrusa")


def join(owner: Api, other: Api, ws_id: str, role: str = "EDITOR") -> None:
    invite = owner.invite(ws_id, role)
    r = other.post(f"/api/v1/invites/{invite['token']}/accept")
    assert r.status_code == 200, r.get_json()


@pytest.fixture
def shared(owner, partner):
    """Ambiente do owner com o partner como EDITOR."""
    ws = owner.create_workspace("Casa")
    join(owner, partner, ws["id"], "EDITOR")
    return ws


def days_from_today(n: int) -> str:
    return (today() + timedelta(days=n)).isoformat()

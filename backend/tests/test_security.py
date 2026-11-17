"""Cabeçalhos de segurança, adulteração de JWT, IDOR e vazamento de erros."""

import base64
import hashlib
import json
import logging
import uuid
from datetime import timedelta

import jwt
import pytest

from app import create_app
from app.extensions import db
from app.models import Invite
from app.timeutil import utcnow

from .conftest import TEST_SECRET, join, login

# --- cabeçalhos -----------------------------------------------------------------


@pytest.mark.parametrize("path", ["/health", "/api/v1/config", "/api/v1/workspaces", "/api/v1/nao-existe"])
def test_security_headers_on_json(client, path):
    r = client.get(path)
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]
    assert "Access-Control-Allow-Origin" not in r.headers  # sem CORS


def test_invite_page_html(client):
    token = "A" * 32
    r = client.get(f"/convite/{token}")
    assert r.status_code == 200
    assert r.mimetype == "text/html"
    html = r.get_data(as_text=True)
    assert f'href="duocash://join/{token}"' in html
    assert "Ainda não tem o app? Peça o APK para quem te convidou." in html
    assert "#6d4fc2" in html
    csp = r.headers["Content-Security-Policy"]
    assert "default-src 'none'" in csp and "script-src" not in csp
    assert "frame-ancestors 'none'" in csp
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "<script" not in html


def test_invite_page_does_not_reveal_workspace(owner, client):
    ws = owner.create_workspace("Segredo do Casal")
    inv = owner.invite(ws["id"])
    html = client.get(f"/convite/{inv['token']}").get_data(as_text=True)
    assert "Segredo do Casal" not in html


@pytest.mark.parametrize("token", ['"><script>alert(1)</script>', "abc", "a" * 65, "<img src=x onerror=1>"])
def test_invite_page_rejects_and_escapes_bad_tokens(client, token):
    r = client.get(f"/convite/{token}")
    assert r.status_code == 404
    html = r.get_data(as_text=True)
    assert "<script>alert" not in html and "onerror" not in html


# --- adulteração de JWT ---------------------------------------------------------


def _payload(user_id, **extra):
    now = utcnow()
    payload = {
        "iss": "duocash-api",
        "aud": "duocash-app",
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    payload.update(extra)
    return payload


def _b64(data: dict) -> str:
    raw = json.dumps(data, default=lambda d: int(d.timestamp())).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _get_me(client, token):
    return client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})


def test_jwt_alg_none_rejected(client, owner):
    token = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(_payload(owner.id))}."
    assert _get_me(client, token).status_code == 401


def test_jwt_wrong_signature_rejected(client, owner):
    token = jwt.encode(_payload(owner.id), "outra-chave-secreta-com-mais-de-32-chars", algorithm="HS256")
    assert _get_me(client, token).status_code == 401


def test_jwt_tampered_payload_rejected(client, owner, partner):
    header, _, signature = owner.tokens["access_token"].split(".")
    forged = f"{header}.{_b64(_payload(partner.id))}.{signature}"
    assert _get_me(client, forged).status_code == 401


@pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning")
def test_jwt_other_algorithm_rejected(client, owner):
    token = jwt.encode(_payload(owner.id), TEST_SECRET, algorithm="HS512")
    assert _get_me(client, token).status_code == 401


def test_refresh_token_cannot_be_used_as_access(client, owner):
    r = _get_me(client, owner.tokens["refresh_token"])
    assert r.status_code == 401
    assert r.get_json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    "change",
    [
        {"aud": "outro-app"},
        {"iss": "outro-emissor"},
        {"type": "admin"},
        {"sub": "nao-e-uuid"},
        {"sub": "00000000-0000-0000-0000-000000000000"},
    ],
)
def test_jwt_bad_claims_rejected(client, owner, change):
    token = jwt.encode(_payload(owner.id, **change), TEST_SECRET, algorithm="HS256")
    assert _get_me(client, token).status_code == 401


@pytest.mark.parametrize("missing", ["exp", "iat", "iss", "aud", "sub", "type"])
def test_jwt_missing_claims_rejected(client, owner, missing):
    payload = _payload(owner.id)
    payload.pop(missing)
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    assert _get_me(client, token).status_code == 401


def test_valid_forged_token_works(client, owner):
    """Controle: um token correto com a chave certa é aceito."""
    token = jwt.encode(_payload(owner.id), TEST_SECRET, algorithm="HS256")
    assert _get_me(client, token).status_code == 200


# --- IDOR -----------------------------------------------------------------------


@pytest.fixture
def victim_data(owner, partner):
    ws = owner.create_workspace("Casa da Ana")
    join(owner, partner, ws["id"], "EDITOR")
    expense = owner.create_expense(ws["id"], description="Privado")
    invite = owner.invite(ws["id"], "VIEWER")
    return ws, expense, invite


def test_idor_other_user_gets_404_everywhere(stranger, victim_data, owner, partner):
    ws, expense, invite = victim_data
    wid, eid = ws["id"], expense["id"]
    attempts = [
        stranger.get(f"/api/v1/workspaces/{wid}"),
        stranger.patch(f"/api/v1/workspaces/{wid}", json={"name": "hack"}),
        stranger.delete(f"/api/v1/workspaces/{wid}"),
        stranger.get(f"/api/v1/workspaces/{wid}/members"),
        stranger.delete(f"/api/v1/workspaces/{wid}/members/{partner.id}"),
        stranger.post(f"/api/v1/workspaces/{wid}/leave"),
        stranger.get(f"/api/v1/workspaces/{wid}/expenses"),
        stranger.post(f"/api/v1/workspaces/{wid}/expenses", json={"amount_cents": 1}),
        stranger.get(f"/api/v1/workspaces/{wid}/summary"),
        stranger.post(f"/api/v1/workspaces/{wid}/invites", json={"role": "EDITOR"}),
        stranger.get(f"/api/v1/workspaces/{wid}/invites"),
        stranger.patch(f"/api/v1/expenses/{eid}", json={"amount_cents": 1}),
        stranger.delete(f"/api/v1/expenses/{eid}"),
        stranger.delete(f"/api/v1/invites/{invite['id']}"),
    ]
    for r in attempts:
        assert r.status_code == 404, (r.request.method, r.request.path, r.get_json())
        assert r.get_json()["error"]["code"] == "not_found"
    assert stranger.get("/api/v1/workspaces").get_json()["items"] == []

    # nada mudou para os donos
    data = owner.get(f"/api/v1/workspaces/{wid}").get_json()
    assert data["name"] == "Casa da Ana" and len(data["members"]) == 2
    listed = owner.get(f"/api/v1/workspaces/{wid}/expenses").get_json()
    assert [e["id"] for e in listed["items"]] == [eid]
    assert len(owner.get(f"/api/v1/workspaces/{wid}/invites").get_json()["items"]) == 1


def test_idor_expense_list_never_mixes_workspaces(owner, stranger):
    ws_a = owner.create_workspace("A")
    ws_b = stranger.create_workspace("B")
    owner.create_expense(ws_a["id"], description="da Ana")
    stranger.create_expense(ws_b["id"], description="da Intrusa")
    items = owner.get(f"/api/v1/workspaces/{ws_a['id']}/expenses").get_json()["items"]
    assert [e["description"] for e in items] == ["da Ana"]


def test_removed_member_loses_access(owner, partner, shared):
    expense = partner.create_expense(shared["id"])
    assert owner.delete(f"/api/v1/workspaces/{shared['id']}/members/{partner.id}").status_code == 204
    assert partner.get(f"/api/v1/workspaces/{shared['id']}").status_code == 404
    assert partner.patch(f"/api/v1/expenses/{expense['id']}", json={"amount_cents": 5}).status_code == 404


# --- armazenamento e erros ------------------------------------------------------


def test_invite_token_stored_only_as_hash(app, owner):
    ws = owner.create_workspace()
    inv = owner.invite(ws["id"])
    with app.app_context():
        row = db.session.get(Invite, uuid.UUID(inv["id"]))
        assert row.token_hash != inv["token"]
        assert len(row.token_hash) == 64
        assert row.token_hash == hashlib.sha256(inv["token"].encode()).hexdigest()


def test_internal_errors_do_not_leak(app, client):
    def boom():
        raise RuntimeError("segredo: postgres://user:senha@db")

    app.view_functions["auth.config"] = lambda: boom()
    r = client.get("/api/v1/config")
    assert r.status_code == 500
    body = r.get_json()
    assert body["error"]["code"] == "internal_error"
    assert "segredo" not in r.get_data(as_text=True)


def test_body_size_limit(owner):
    ws = owner.create_workspace()
    r = owner.post(f"/api/v1/workspaces/{ws['id']}/expenses", json={"description": "x" * 20000})
    assert r.status_code == 413
    assert r.get_json()["error"]["code"] == "payload_too_large"


def test_short_secret_key_refused_outside_tests():
    with pytest.raises(RuntimeError):
        create_app({"SECRET_KEY": "curta", "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})


def test_405_is_json(client):
    r = client.put("/api/v1/workspaces")
    assert r.status_code == 405
    assert r.get_json()["error"]["code"] == "method_not_allowed"


def test_logs_have_no_tokens_or_emails(client, caplog, owner):
    caplog.set_level(logging.INFO)  # captura log de segurança e de acesso
    ws = owner.create_workspace()
    inv = owner.invite(ws["id"])
    other = login(client, "Carla", "carla.secreta@example.com")
    other.post(f"/api/v1/invites/{inv['token']}/accept")
    owner.create_expense(ws["id"], description="Presente surpresa", amount_cents=98765)
    text = caplog.text
    assert "invite_created" in text and "invite_accepted" in text and "login_success" in text
    assert "/api/v1/invites/<token>/accept" in text  # acesso logado pelo molde da rota
    assert inv["token"] not in text
    assert "carla.secreta" not in text
    assert "Presente surpresa" not in text and "98765" not in text
    assert owner.tokens["access_token"] not in text


def test_permission_denied_is_logged(client, caplog, owner, partner, shared):
    caplog.set_level(logging.INFO, logger="duocash.security")
    partner.post(f"/api/v1/workspaces/{shared['id']}/invites", json={"role": "EDITOR"})
    assert "permission_denied" in caplog.text

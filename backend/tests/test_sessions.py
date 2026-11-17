"""Refresh tokens: rotação, detecção de reuso, logout e revogação de sessões."""

import logging
import uuid
from datetime import timedelta

import jwt
import sqlalchemy as sa

from app.extensions import db
from app.models import RefreshToken, User
from app.security import hash_token
from app.timeutil import utcnow

from .conftest import TEST_SECRET, login


def _refresh(client, token):
    return client.post("/api/v1/auth/refresh", json={"refresh_token": token})


def _me(client, access):
    return client.get("/api/v1/me", headers={"Authorization": f"Bearer {access}"})


def _jti_hash(token):
    return hash_token(jwt.decode(token, options={"verify_signature": False})["jti"])


def test_refresh_token_is_stored_hashed(app, client):
    api = login(client)
    token = api.tokens["refresh_token"]
    raw_jti = jwt.decode(token, options={"verify_signature": False})["jti"]
    with app.app_context():
        rows = db.session.execute(sa.select(RefreshToken)).scalars().all()
        assert len(rows) == 1
        assert rows[0].jti == hash_token(raw_jti) != raw_jti
        assert rows[0].used_at is None and rows[0].revoked_at is None


def test_old_refresh_token_rejected_after_rotation(client):
    api = login(client)
    old = api.tokens["refresh_token"]
    r1 = _refresh(client, old)
    assert r1.status_code == 200
    r2 = _refresh(client, old)
    assert r2.status_code == 401
    assert r2.get_json()["error"]["code"] == "unauthorized"


def test_rotation_chain_works(client):
    api = login(client)
    token = api.tokens["refresh_token"]
    for _ in range(3):
        r = _refresh(client, token)
        assert r.status_code == 200
        token = r.get_json()["refresh_token"]
        assert _me(client, r.get_json()["access_token"]).status_code == 200


def test_reuse_revokes_whole_family(app, client, caplog):
    caplog.set_level(logging.INFO, logger="duocash.security")
    api = login(client)
    stolen = api.tokens["refresh_token"]
    legit = _refresh(client, stolen).get_json()["refresh_token"]  # o app renova normalmente
    assert _refresh(client, stolen).status_code == 401  # atacante reusa o antigo
    # a sessão legítima também cai (a família inteira foi revogada)
    assert _refresh(client, legit).status_code == 401
    assert "refresh_reuse_detected" in caplog.text
    with app.app_context():
        rows = db.session.execute(sa.select(RefreshToken)).scalars().all()
        assert len(rows) == 2
        assert all(r.revoked_at is not None for r in rows)


def test_reuse_does_not_affect_other_sessions(client):
    phone = login(client, email="mesma@example.com", name="Mesma")
    tablet = login(client, email="mesma@example.com", name="Mesma")  # novo login = nova família
    old = phone.tokens["refresh_token"]
    _refresh(client, old)
    _refresh(client, old)  # reuso derruba só a família do celular
    assert _refresh(client, tablet.tokens["refresh_token"]).status_code == 200


def test_logout_revokes_family(client, caplog):
    caplog.set_level(logging.INFO, logger="duocash.security")
    api = login(client)
    rotated = _refresh(client, api.tokens["refresh_token"]).get_json()["refresh_token"]
    r = client.post("/api/v1/auth/logout", json={"refresh_token": rotated})
    assert r.status_code == 204
    assert _refresh(client, rotated).status_code == 401
    assert "logout" in caplog.text
    # idempotente e sem auth
    assert client.post("/api/v1/auth/logout", json={"refresh_token": rotated}).status_code == 204


def test_logout_accepts_garbage_but_requires_field(client):
    assert client.post("/api/v1/auth/logout", json={"refresh_token": "lixo"}).status_code == 204
    r = client.post("/api/v1/auth/logout", json={})
    assert r.status_code == 400
    assert "refresh_token" in r.get_json()["error"]["fields"]


def test_unknown_jti_rejected(app, client):
    api = login(client)
    payload = jwt.decode(api.tokens["refresh_token"], options={"verify_signature": False})
    payload["jti"] = uuid.uuid4().hex  # assinado corretamente, mas nunca emitido
    forged = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    assert _refresh(client, forged).status_code == 401


def test_refresh_without_jti_rejected(client):
    api = login(client)
    payload = jwt.decode(api.tokens["refresh_token"], options={"verify_signature": False})
    payload.pop("jti")
    assert _refresh(client, jwt.encode(payload, TEST_SECRET, algorithm="HS256")).status_code == 401


def test_revoked_row_rejected(app, client):
    api = login(client)
    token = api.tokens["refresh_token"]
    with app.app_context():
        row = db.session.get(RefreshToken, _jti_hash(token))
        row.revoked_at = utcnow()
        db.session.commit()
    assert _refresh(client, token).status_code == 401


def test_expired_row_rejected(app, client):
    api = login(client)
    token = api.tokens["refresh_token"]
    with app.app_context():
        row = db.session.get(RefreshToken, _jti_hash(token))
        row.expires_at = utcnow() - timedelta(seconds=1)
        db.session.commit()
    assert _refresh(client, token).status_code == 401


def test_sessions_revoked_at_blocks_old_tokens(app, client):
    api = login(client)
    with app.app_context():
        user = db.session.get(User, uuid.UUID(api.id))
        user.sessions_revoked_at = utcnow() + timedelta(seconds=2)  # tudo emitido antes disso cai
        db.session.commit()
    r = _me(client, api.tokens["access_token"])
    assert r.status_code == 401
    assert r.get_json()["error"]["code"] == "unauthorized"
    assert _refresh(client, api.tokens["refresh_token"]).status_code == 401


def test_cli_revoke_sessions_and_purge(app, client):
    api = login(client)
    runner = app.test_cli_runner()
    result = runner.invoke(args=["revoke-sessions", api.id])
    assert result.exit_code == 0, result.output
    # o iat é em segundos; um token emitido no mesmo segundo da revogação ainda passa,
    # então conferimos pelo estado do refresh token (revogado).
    assert _refresh(client, api.tokens["refresh_token"]).status_code == 401

    with app.app_context():
        db.session.execute(sa.update(RefreshToken).values(expires_at=utcnow() - timedelta(days=1)))
        db.session.commit()
    result = runner.invoke(args=["purge-refresh-tokens"])
    assert result.exit_code == 0 and "1 refresh tokens" in result.output
    with app.app_context():
        assert db.session.query(RefreshToken).count() == 0


def test_cli_revoke_unknown_user(app):
    result = app.test_cli_runner().invoke(args=["revoke-sessions", str(uuid.uuid4())])
    assert result.exit_code != 0


def test_new_login_starts_new_family(app, client):
    a = login(client, email="fam@example.com", name="F")
    b = login(client, email="fam@example.com", name="F")
    with app.app_context():
        fa = db.session.get(RefreshToken, _jti_hash(a.tokens["refresh_token"])).family_id
        fb = db.session.get(RefreshToken, _jti_hash(b.tokens["refresh_token"])).family_id
    assert fa != fb
    rotated = _refresh(client, a.tokens["refresh_token"]).get_json()["refresh_token"]
    with app.app_context():
        assert db.session.get(RefreshToken, _jti_hash(rotated)).family_id == fa

import uuid
from datetime import timedelta

import pytest

from app.extensions import db
from app.models import Invite
from app.timeutil import utcnow

from .conftest import login


def _set_invite(app, invite_id, **values):
    with app.app_context():
        row = db.session.get(Invite, uuid.UUID(invite_id))
        for k, v in values.items():
            setattr(row, k, v)
        db.session.commit()


def test_create_invite_response(owner):
    ws = owner.create_workspace()
    inv = owner.invite(ws["id"], "VIEWER")
    assert inv["role"] == "VIEWER"
    assert len(inv["token"]) == 32  # token_urlsafe(24)
    assert inv["app_url"] == f"duocash://join/{inv['token']}"
    assert inv["share_url"] == f"https://duocash.example.com/convite/{inv['token']}"
    assert inv["expires_at"].endswith("Z")


def test_tokens_are_unique(owner):
    ws = owner.create_workspace()
    tokens = {owner.invite(ws["id"])["token"] for _ in range(20)}
    assert len(tokens) == 20


def test_preview(owner, partner):
    ws = owner.create_workspace("Viagem", icon="✈️")
    inv = owner.invite(ws["id"], "VIEWER")
    r = partner.get(f"/api/v1/invites/{inv['token']}")
    assert r.status_code == 200
    assert r.get_json() == {
        "workspace_name": "Viagem",
        "workspace_icon": "✈️",
        "role": "VIEWER",
        "invited_by": "Ana",
        "expires_at": inv["expires_at"],
    }


def test_preview_requires_auth(client, owner):
    ws = owner.create_workspace()
    inv = owner.invite(ws["id"])
    assert client.get(f"/api/v1/invites/{inv['token']}").status_code == 401


def test_accept_adds_member_with_invite_role(owner, partner):
    ws = owner.create_workspace()
    inv = owner.invite(ws["id"], "VIEWER")
    r = partner.post(f"/api/v1/invites/{inv['token']}/accept")
    assert r.status_code == 200
    body = r.get_json()["workspace"]
    assert body["id"] == ws["id"]
    assert body["role"] == "VIEWER"
    assert [m["user_id"] for m in body["members"]] == [owner.id, partner.id]


def test_invite_is_single_use(client, owner, partner):
    ws = owner.create_workspace()
    inv = owner.invite(ws["id"])
    assert partner.post(f"/api/v1/invites/{inv['token']}/accept").status_code == 200
    third = login(client, "Terceiro")
    r = third.post(f"/api/v1/invites/{inv['token']}/accept")
    assert r.status_code == 410
    assert r.get_json()["error"]["code"] == "invite_used"
    assert third.get(f"/api/v1/invites/{inv['token']}").status_code == 410
    assert third.get(f"/api/v1/workspaces/{ws['id']}").status_code == 404


def test_already_member_does_not_consume(client, owner, partner):
    ws = owner.create_workspace()
    inv = owner.invite(ws["id"])
    r = owner.post(f"/api/v1/invites/{inv['token']}/accept")  # o dono abriu o próprio link
    assert r.status_code == 200
    assert r.get_json()["workspace"]["role"] == "OWNER"
    assert partner.post(f"/api/v1/invites/{inv['token']}/accept").status_code == 200


def test_expired_invite(app, owner, partner):
    ws = owner.create_workspace()
    inv = owner.invite(ws["id"])
    _set_invite(app, inv["id"], expires_at=utcnow() - timedelta(seconds=1))
    for r in (partner.get(f"/api/v1/invites/{inv['token']}"), partner.post(f"/api/v1/invites/{inv['token']}/accept")):
        assert r.status_code == 410
        assert r.get_json()["error"]["code"] == "invite_expired"
    assert owner.get(f"/api/v1/workspaces/{ws['id']}/invites").get_json()["items"] == []


def test_invite_ttl_from_config(app, owner):
    ws = owner.create_workspace()
    before = utcnow()
    inv = owner.invite(ws["id"])
    with app.app_context():
        row = db.session.get(Invite, uuid.UUID(inv["id"]))
        from app.timeutil import as_utc

        delta = as_utc(row.expires_at) - before
    assert timedelta(minutes=59) < delta <= timedelta(minutes=60, seconds=5)


def test_unknown_token_404(partner):
    for token in ["x" * 32, "curto", "nao-existe-mesmo-esse-token-aqui"]:
        assert partner.post(f"/api/v1/invites/{token}/accept").status_code == 404
        assert partner.get(f"/api/v1/invites/{token}").status_code == 404


def test_cancel_invite(owner, partner):
    ws = owner.create_workspace()
    inv = owner.invite(ws["id"])
    assert owner.delete(f"/api/v1/invites/{inv['id']}").status_code == 204
    assert owner.delete(f"/api/v1/invites/{inv['id']}").status_code == 204  # idempotente
    r = partner.post(f"/api/v1/invites/{inv['token']}/accept")
    assert r.status_code == 410
    assert r.get_json()["error"]["code"] == "invite_used"
    assert owner.get(f"/api/v1/workspaces/{ws['id']}/invites").get_json()["items"] == []


def test_cancel_unknown_invite(owner):
    assert owner.delete(f"/api/v1/invites/{uuid.uuid4()}").status_code == 404


def test_list_only_pending(app, client, owner, partner):
    ws = owner.create_workspace()
    used = owner.invite(ws["id"])
    expired = owner.invite(ws["id"])
    cancelled = owner.invite(ws["id"])
    pending = owner.invite(ws["id"], "VIEWER")
    partner.post(f"/api/v1/invites/{used['token']}/accept")
    _set_invite(app, expired["id"], expires_at=utcnow() - timedelta(minutes=1))
    owner.delete(f"/api/v1/invites/{cancelled['id']}")
    items = owner.get(f"/api/v1/workspaces/{ws['id']}/invites").get_json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == pending["id"]
    assert set(item) == {"id", "role", "created_at", "expires_at", "created_by"}
    assert item["created_by"] == owner.id
    assert "token" not in item


def test_deleted_workspace_invite_is_404(owner, partner):
    ws = owner.create_workspace()
    inv = owner.invite(ws["id"])
    owner.delete(f"/api/v1/workspaces/{ws['id']}")
    assert partner.post(f"/api/v1/invites/{inv['token']}/accept").status_code == 404


@pytest.mark.parametrize("role", ["EDITOR", "VIEWER"])
def test_role_cannot_be_overridden_by_client(owner, partner, role):
    ws = owner.create_workspace()
    inv = owner.invite(ws["id"], role)
    r = partner.post(f"/api/v1/invites/{inv['token']}/accept", json={"role": "OWNER"})
    assert r.get_json()["workspace"]["role"] == role

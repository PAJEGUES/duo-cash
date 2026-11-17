"""Ambiente arquivado é somente leitura."""

import logging

import pytest

from .conftest import expense_body, login


@pytest.fixture
def archived(owner, partner, shared):
    expense = owner.create_expense(shared["id"])
    pending = owner.invite(shared["id"], "VIEWER")
    r = owner.patch(f"/api/v1/workspaces/{shared['id']}", json={"archived": True})
    assert r.status_code == 200
    return shared["id"], expense, pending


def _assert_archived(r):
    assert r.status_code == 409, r.get_json()
    err = r.get_json()["error"]
    assert err["code"] == "workspace_archived"
    assert "arquivado" in err["message"]


def test_writes_blocked(archived, owner, partner):
    wid, expense, _ = archived
    for api in (owner, partner):
        _assert_archived(api.post(f"/api/v1/workspaces/{wid}/expenses", json=expense_body()))
        _assert_archived(api.patch(f"/api/v1/expenses/{expense['id']}", json={"amount_cents": 1}))
        _assert_archived(api.delete(f"/api/v1/expenses/{expense['id']}"))
    _assert_archived(owner.post(f"/api/v1/workspaces/{wid}/invites", json={"role": "EDITOR"}))


def test_reads_still_work(archived, owner, partner):
    wid, expense, _ = archived
    assert partner.get(f"/api/v1/workspaces/{wid}").status_code == 200
    items = partner.get(f"/api/v1/workspaces/{wid}/expenses").get_json()["items"]
    assert [e["id"] for e in items] == [expense["id"]]
    assert partner.get(f"/api/v1/workspaces/{wid}/summary").status_code == 200


def test_viewer_still_gets_403_not_409(client, owner):
    """Permissão é conferida antes do estado do ambiente."""
    viewer = login(client)
    ws = owner.create_workspace("Outro")
    inv = owner.invite(ws["id"], "VIEWER")
    viewer.post(f"/api/v1/invites/{inv['token']}/accept")
    owner.patch(f"/api/v1/workspaces/{ws['id']}", json={"archived": True})
    r = viewer.post(f"/api/v1/workspaces/{ws['id']}/expenses", json=expense_body())
    assert r.status_code == 403


def test_archiving_cancels_pending_invites(archived, owner, client):
    wid, _, pending = archived
    owner.patch(f"/api/v1/workspaces/{wid}", json={"archived": False})
    assert owner.get(f"/api/v1/workspaces/{wid}/invites").get_json()["items"] == []
    newcomer = login(client)
    r = newcomer.post(f"/api/v1/invites/{pending['token']}/accept")
    assert r.status_code == 410
    assert r.get_json()["error"]["code"] == "invite_used"


def test_accept_and_preview_on_archived(owner, client):
    ws = owner.create_workspace()
    inv = owner.invite(ws["id"])
    owner.patch(f"/api/v1/workspaces/{ws['id']}", json={"archived": True})
    newcomer = login(client)
    assert newcomer.get(f"/api/v1/invites/{inv['token']}").status_code == 410
    _assert_archived(newcomer.post(f"/api/v1/invites/{inv['token']}/accept"))


def test_owner_can_unarchive_and_write_again(archived, owner):
    wid, expense, _ = archived
    r = owner.patch(f"/api/v1/workspaces/{wid}", json={"archived": False})
    assert r.status_code == 200 and r.get_json()["archived_at"] is None
    assert owner.patch(f"/api/v1/expenses/{expense['id']}", json={"amount_cents": 5}).status_code == 200
    owner.create_expense(wid)


def test_owner_can_rename_and_delete_archived(archived, owner):
    wid, _, _ = archived
    assert owner.patch(f"/api/v1/workspaces/{wid}", json={"name": "Antigo"}).status_code == 200
    assert owner.delete(f"/api/v1/workspaces/{wid}").status_code == 204


def test_members_can_leave_archived(archived, partner):
    wid, _, _ = archived
    assert partner.post(f"/api/v1/workspaces/{wid}/leave").status_code == 204


def test_workspace_audit_events(owner, partner, shared, caplog):
    caplog.set_level(logging.INFO, logger="duocash.security")
    wid = shared["id"]
    owner.patch(f"/api/v1/workspaces/{wid}", json={"name": "Novo"})
    owner.patch(f"/api/v1/workspaces/{wid}", json={"archived": True})
    owner.patch(f"/api/v1/workspaces/{wid}", json={"archived": False})
    partner.post(f"/api/v1/workspaces/{wid}/leave")
    for event in ("workspace_renamed", "workspace_archived", "workspace_unarchived", "workspace_left"):
        assert event in caplog.text

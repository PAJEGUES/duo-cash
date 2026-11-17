from .conftest import join, login


def test_create_workspace(owner):
    ws = owner.create_workspace("Casa")
    assert ws["name"] == "Casa"
    assert ws["icon"] == "🏠"
    assert ws["currency"] == "BRL"
    assert ws["role"] == "OWNER"
    assert ws["owner_id"] == owner.id
    assert ws["archived_at"] is None
    assert ws["month_total_cents"] == 0
    assert [m["user_id"] for m in ws["members"]] == [owner.id]
    assert set(ws["members"][0]) == {"user_id", "display_name", "email", "avatar_url", "role", "joined_at"}


def test_custom_icon(owner):
    assert owner.create_workspace("Viagem", icon="✈️")["icon"] == "✈️"


def test_list_ordered_and_excludes_archived_and_deleted(owner):
    a = owner.create_workspace("A")
    b = owner.create_workspace("B")
    c = owner.create_workspace("C")
    owner.patch(f"/api/v1/workspaces/{b['id']}", json={"archived": True})
    owner.delete(f"/api/v1/workspaces/{c['id']}")
    names = [w["name"] for w in owner.get("/api/v1/workspaces").get_json()["items"]]
    assert names == ["A"]
    names = [w["name"] for w in owner.get("/api/v1/workspaces?include_archived=1").get_json()["items"]]
    assert names == ["A", "B"]
    assert owner.get(f"/api/v1/workspaces/{c['id']}").status_code == 404
    assert owner.get(f"/api/v1/workspaces/{a['id']}").status_code == 200


def test_patch_workspace(owner):
    ws = owner.create_workspace("Casa")
    r = owner.patch(f"/api/v1/workspaces/{ws['id']}", json={"name": " Lar ", "icon": "🏡", "archived": True})
    body = r.get_json()
    assert r.status_code == 200
    assert body["name"] == "Lar" and body["icon"] == "🏡" and body["archived_at"] is not None
    body = owner.patch(f"/api/v1/workspaces/{ws['id']}", json={"archived": False}).get_json()
    assert body["archived_at"] is None


def test_patch_archived_must_be_bool(owner):
    ws = owner.create_workspace()
    assert owner.patch(f"/api/v1/workspaces/{ws['id']}", json={"archived": "yes"}).status_code == 400


def test_members_ordered_by_joined_at(client, owner, partner):
    ws = owner.create_workspace()
    join(owner, partner, ws["id"], "EDITOR")
    third = login(client, "Carla")
    join(owner, third, ws["id"], "VIEWER")
    items = partner.get(f"/api/v1/workspaces/{ws['id']}/members").get_json()["items"]
    assert [(m["display_name"], m["role"]) for m in items] == [
        ("Ana", "OWNER"),
        ("Bruno", "EDITOR"),
        ("Carla", "VIEWER"),
    ]
    ws_body = third.get(f"/api/v1/workspaces/{ws['id']}").get_json()
    assert [m["user_id"] for m in ws_body["members"]] == [owner.id, partner.id, third.id]
    listed = third.get("/api/v1/workspaces").get_json()["items"][0]
    assert [m["user_id"] for m in listed["members"]] == [owner.id, partner.id, third.id]


def test_deleted_workspace_hidden_from_members(owner, partner, shared):
    owner.delete(f"/api/v1/workspaces/{shared['id']}")
    assert partner.get("/api/v1/workspaces").get_json()["items"] == []
    assert partner.get(f"/api/v1/workspaces/{shared['id']}/expenses").status_code == 404

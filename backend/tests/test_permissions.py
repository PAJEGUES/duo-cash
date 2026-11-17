"""Matriz de permissões (docs/requisitos.md, seção "Permissões").

| Ação                                     | Dono | Controle total | Somente leitura |
| Ver lançamentos e relatórios             |  ✅  |       ✅       |       ✅        |
| Criar lançamento                         |  ✅  |       ✅       |       ❌        |
| Editar/excluir lançamento                |  ✅  |       ✅       |       ❌        |
| Gerar convite (link/QR)                  |  ✅  |       ❌       |       ❌        |
| Remover acesso de um membro              |  ✅  |       ❌       |       ❌        |
| Renomear, arquivar ou excluir o ambiente |  ✅  |       ❌       |       ❌        |
"""

import pytest

from .conftest import expense_body, join, login

ROLES = ["OWNER", "EDITOR", "VIEWER"]


@pytest.fixture
def setup(client):
    """Ambiente com dono, editor e leitor + um gasto de cada pessoa que escreve."""
    owner = login(client, "Dono")
    editor = login(client, "Editor")
    viewer = login(client, "Leitor")
    extra = login(client, "Extra")
    ws = owner.create_workspace()
    join(owner, editor, ws["id"], "EDITOR")
    join(owner, viewer, ws["id"], "VIEWER")
    join(owner, extra, ws["id"], "VIEWER")
    users = {"OWNER": owner, "EDITOR": editor, "VIEWER": viewer}
    return ws["id"], users, extra


def _do(action, wid, actor, users, extra):
    owner = users["OWNER"]
    if action == "view_expenses":
        return actor.get(f"/api/v1/workspaces/{wid}/expenses")
    if action == "view_summary":
        return actor.get(f"/api/v1/workspaces/{wid}/summary")
    if action == "view_workspace":
        return actor.get(f"/api/v1/workspaces/{wid}")
    if action == "view_members":
        return actor.get(f"/api/v1/workspaces/{wid}/members")
    if action == "create_expense":
        return actor.post(f"/api/v1/workspaces/{wid}/expenses", json=expense_body())
    if action in ("edit_own_expense", "delete_own_expense", "edit_other_expense", "delete_other_expense"):
        author = actor if "own" in action else (users["EDITOR"] if actor is owner else owner)
        if author is users["VIEWER"]:
            author = owner  # leitor não tem gasto próprio; usa o do dono
        expense = author.create_expense(wid)
        if action.startswith("edit"):
            return actor.patch(f"/api/v1/expenses/{expense['id']}", json={"amount_cents": 777})
        return actor.delete(f"/api/v1/expenses/{expense['id']}")
    if action == "create_invite":
        return actor.post(f"/api/v1/workspaces/{wid}/invites", json={"role": "VIEWER"})
    if action == "list_invites":
        return actor.get(f"/api/v1/workspaces/{wid}/invites")
    if action == "cancel_invite":
        inv = owner.invite(wid, "VIEWER")
        return actor.delete(f"/api/v1/invites/{inv['id']}")
    if action == "remove_member":
        return actor.delete(f"/api/v1/workspaces/{wid}/members/{extra.id}")
    if action == "rename":
        return actor.patch(f"/api/v1/workspaces/{wid}", json={"name": "Novo nome"})
    if action == "archive":
        return actor.patch(f"/api/v1/workspaces/{wid}", json={"archived": True})
    if action == "delete_workspace":
        return actor.delete(f"/api/v1/workspaces/{wid}")
    raise AssertionError(action)


# ação -> papéis permitidos
MATRIX = {
    "view_expenses": {"OWNER", "EDITOR", "VIEWER"},
    "view_summary": {"OWNER", "EDITOR", "VIEWER"},
    "view_workspace": {"OWNER", "EDITOR", "VIEWER"},
    "view_members": {"OWNER", "EDITOR", "VIEWER"},
    "create_expense": {"OWNER", "EDITOR"},
    "edit_own_expense": {"OWNER", "EDITOR"},
    "delete_own_expense": {"OWNER", "EDITOR"},
    "edit_other_expense": {"OWNER", "EDITOR"},
    "delete_other_expense": {"OWNER", "EDITOR"},
    "create_invite": {"OWNER"},
    "list_invites": {"OWNER"},
    "cancel_invite": {"OWNER"},
    "remove_member": {"OWNER"},
    "rename": {"OWNER"},
    "archive": {"OWNER"},
    "delete_workspace": {"OWNER"},
}

CASES = [(action, role, role in allowed) for action, allowed in MATRIX.items() for role in ROLES]


@pytest.mark.parametrize("action,role,allowed", CASES, ids=[f"{a}-{r}" for a, r, _ in CASES])
def test_permission_matrix(setup, action, role, allowed):
    wid, users, extra = setup
    r = _do(action, wid, users[role], users, extra)
    if allowed:
        assert r.status_code in (200, 201, 204), r.get_json()
    else:
        assert r.status_code == 403, r.get_json()
        assert r.get_json()["error"]["code"] == "forbidden"


def test_role_reported_per_caller(setup):
    wid, users, _ = setup
    for role, api in users.items():
        assert api.get(f"/api/v1/workspaces/{wid}").get_json()["role"] == role


def test_viewer_write_attempt_changes_nothing(setup):
    wid, users, _ = setup
    expense = users["OWNER"].create_expense(wid, amount_cents=500)
    users["VIEWER"].patch(f"/api/v1/expenses/{expense['id']}", json={"amount_cents": 1})
    users["VIEWER"].delete(f"/api/v1/expenses/{expense['id']}")
    items = users["OWNER"].get(f"/api/v1/workspaces/{wid}/expenses").get_json()["items"]
    assert [(e["id"], e["amount_cents"]) for e in items] == [(expense["id"], 500)]


def test_owner_cannot_be_removed_or_leave(setup):
    wid, users, _ = setup
    owner = users["OWNER"]
    r = owner.delete(f"/api/v1/workspaces/{wid}/members/{owner.id}")
    assert r.status_code == 400
    assert owner.post(f"/api/v1/workspaces/{wid}/leave").status_code == 400


@pytest.mark.parametrize("role", ["EDITOR", "VIEWER"])
def test_non_owner_can_leave(setup, role):
    wid, users, _ = setup
    assert users[role].post(f"/api/v1/workspaces/{wid}/leave").status_code == 204
    assert users[role].get(f"/api/v1/workspaces/{wid}").status_code == 404
    members = users["OWNER"].get(f"/api/v1/workspaces/{wid}/members").get_json()["items"]
    assert users[role].id not in [m["user_id"] for m in members]


def test_remove_unknown_member_404(setup, client):
    wid, users, _ = setup
    outsider = login(client)
    assert users["OWNER"].delete(f"/api/v1/workspaces/{wid}/members/{outsider.id}").status_code == 404

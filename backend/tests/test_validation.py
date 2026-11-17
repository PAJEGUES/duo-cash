"""Validação de dados: valores-limite e entradas malformadas."""

import pytest

from app.constants import CATEGORIES, ICON_KEYS, MAX_AMOUNT_CENTS
from app.validation import check_amount, check_description

from .conftest import days_from_today, expense_body

MAX = MAX_AMOUNT_CENTS


def post_expense(api, ws_id, **fields):
    return api.post(f"/api/v1/workspaces/{ws_id}/expenses", json=expense_body(**fields))


def assert_field_error(resp, field):
    assert resp.status_code == 400, resp.get_json()
    err = resp.get_json()["error"]
    assert err["code"] == "validation_error"
    assert field in err["fields"]


# --- valor em centavos ------------------------------------------------------


@pytest.mark.parametrize("amount", [1, 2, 999, 123456, MAX - 1, MAX])
def test_amount_accepted(owner, amount):
    ws = owner.create_workspace()
    r = post_expense(owner, ws["id"], amount_cents=amount)
    assert r.status_code == 201
    assert r.get_json()["amount_cents"] == amount


@pytest.mark.parametrize(
    "amount",
    [0, -1, -100, MAX + 1, 10**20, 10.5, 1.0, 0.1, True, False, "1000", "10,00", None, [], {}, "", float("1e3")],
)
def test_amount_rejected(owner, amount):
    ws = owner.create_workspace()
    assert_field_error(post_expense(owner, ws["id"], amount_cents=amount), "amount_cents")


def test_check_amount_unit():
    assert check_amount(1) == (1, None)
    assert check_amount(True)[1] is not None  # bool é subclasse de int: recusado
    assert check_amount(1.0)[1] is not None


# --- descrição ----------------------------------------------------------------


@pytest.mark.parametrize(
    "description,expected",
    [
        ("a", "a"),
        ("x" * 100, "x" * 100),
        ("  Mercado  ", "Mercado"),
        ("🍕" * 100, "🍕" * 100),
        ("Pão de queijo ☕", "Pão de queijo ☕"),
        ("  " + "y" * 100 + "  ", "y" * 100),  # espaços nas pontas não contam
    ],
)
def test_description_accepted(owner, description, expected):
    ws = owner.create_workspace()
    r = post_expense(owner, ws["id"], description=description)
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["description"] == expected


@pytest.mark.parametrize(
    "description",
    ["", " ", "   \t\n ", "x" * 101, "🍕" * 101, 123, None, ["a"], {"a": 1}],
)
def test_description_rejected(owner, description):
    ws = owner.create_workspace()
    assert_field_error(post_expense(owner, ws["id"], description=description), "description")


def test_check_description_unit():
    assert check_description("x" * 100)[1] is None
    assert check_description("x" * 101)[1] is not None


# --- data -----------------------------------------------------------------------


@pytest.mark.parametrize("spent_at", ["2000-01-01", "2024-02-29", days_from_today(0), days_from_today(31)])
def test_date_accepted(owner, spent_at):
    ws = owner.create_workspace()
    r = post_expense(owner, ws["id"], spent_at=spent_at)
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["spent_at"] == spent_at


@pytest.mark.parametrize(
    "spent_at",
    [
        "1999-12-31",
        days_from_today(32),
        "2023-02-29",
        "2024-13-01",
        "2024-00-10",
        "2024-01-32",
        "24-01-01",
        "2024/01/01",
        "01/01/2024",
        "2024-01-01T10:00:00",
        "hoje",
        "",
        20240101,
        None,
    ],
)
def test_date_rejected(owner, spent_at):
    ws = owner.create_workspace()
    assert_field_error(post_expense(owner, ws["id"], spent_at=spent_at), "spent_at")


# --- categoria e ícone ----------------------------------------------------------


def test_exactly_17_categories():
    assert len(CATEGORIES) == 17
    assert len(set(CATEGORIES)) == 17


@pytest.mark.parametrize("category", CATEGORIES)
def test_every_category_accepted(owner, category):
    ws = owner.create_workspace()
    assert post_expense(owner, ws["id"], category=category).status_code == 201


@pytest.mark.parametrize("category", ["alimentacao", "LAZER ", "OUTROS", "", None, 5, ["LAZER"]])
def test_category_rejected(owner, category):
    ws = owner.create_workspace()
    assert_field_error(post_expense(owner, ws["id"], category=category), "category")


@pytest.mark.parametrize("icon_key", [*ICON_KEYS, None])
def test_icon_accepted(owner, icon_key):
    ws = owner.create_workspace()
    r = post_expense(owner, ws["id"], category="LAZER", icon_key=icon_key)
    assert r.status_code == 201
    assert r.get_json()["icon_key"] == icon_key


@pytest.mark.parametrize("icon_key", ["Cinema", "foguete", "", 1, ["cinema"]])
def test_icon_rejected(owner, icon_key):
    ws = owner.create_workspace()
    assert_field_error(post_expense(owner, ws["id"], icon_key=icon_key), "icon_key")


def test_missing_fields_all_reported(owner):
    ws = owner.create_workspace()
    r = owner.post(f"/api/v1/workspaces/{ws['id']}/expenses", json={})
    assert r.status_code == 400
    assert set(r.get_json()["error"]["fields"]) == {"amount_cents", "spent_at", "description", "category"}


def test_author_from_client_is_ignored(owner, partner):
    ws = owner.create_workspace()
    r = post_expense(owner, ws["id"], author_id=partner.id, author={"id": partner.id})
    assert r.status_code == 201
    assert r.get_json()["author"]["id"] == owner.id


# --- caminhos, JSON e query string ---------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/workspaces/not-a-uuid",
        "/api/v1/workspaces/123",
        "/api/v1/workspaces/00000000-0000-0000-0000-00000000000g",
        "/api/v1/workspaces/'%20OR%201=1--/expenses",
        "/api/v1/workspaces/00000000-0000-0000-0000-000000000000",
    ],
)
def test_bad_uuid_in_path_is_404(owner, path):
    r = owner.get(path)
    assert r.status_code == 404
    assert r.get_json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "raw,content_type",
    [
        ("{bad json", "application/json"),
        ("", "application/json"),
        ("[1, 2, 3]", "application/json"),
        ('"texto"', "application/json"),
        ("null", "application/json"),
        ("amount_cents=100", "application/x-www-form-urlencoded"),
    ],
)
def test_malformed_json(owner, raw, content_type):
    ws = owner.create_workspace()
    r = owner.client.post(
        f"/api/v1/workspaces/{ws['id']}/expenses",
        data=raw,
        headers={**owner.headers, "Content-Type": content_type},
    )
    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "invalid_json"


@pytest.mark.parametrize(
    "query,field",
    [
        ("month=2026-13", "month"),
        ("month=2026-1", "month"),
        ("month=abc", "month"),
    ],
)
def test_bad_month_param(owner, query, field):
    ws = owner.create_workspace()
    r = owner.get(f"/api/v1/workspaces/{ws['id']}/summary?{query}")
    assert_field_error(r, field)


@pytest.mark.parametrize(
    "query,field",
    [
        ("limit=0", "limit"),
        ("limit=201", "limit"),
        ("limit=abc", "limit"),
        ("offset=-1", "offset"),
        ("date_from=2024-02-30", "date_from"),
        ("date_to=ontem", "date_to"),
        ("amount_min=1.5", "amount_min"),
        ("amount_max=-5", "amount_max"),
        ("author_id=nope", "author_id"),
        ("category=FOO", "category"),
    ],
)
def test_bad_list_params(owner, query, field):
    ws = owner.create_workspace()
    assert_field_error(owner.get(f"/api/v1/workspaces/{ws['id']}/expenses?{query}"), field)


@pytest.mark.parametrize("name", ["", "   ", "x" * 61, None, 5])
def test_workspace_name_rejected(owner, name):
    r = owner.post("/api/v1/workspaces", json={"name": name})
    assert_field_error(r, "name")


@pytest.mark.parametrize("name", ["A", "x" * 60, "Viagem Chile 2026 🇨🇱"])
def test_workspace_name_accepted(owner, name):
    r = owner.post("/api/v1/workspaces", json={"name": name})
    assert r.status_code == 201


@pytest.mark.parametrize("role", ["OWNER", "editor", "ADMIN", None, ""])
def test_invite_role_rejected(owner, role):
    ws = owner.create_workspace()
    r = owner.post(f"/api/v1/workspaces/{ws['id']}/invites", json={"role": role})
    assert_field_error(r, "role")

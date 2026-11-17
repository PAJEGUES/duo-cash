import uuid

from app.extensions import db
from app.models import Expense

from .conftest import days_from_today, expense_body


def test_create_expense_shape(owner):
    ws = owner.create_workspace()
    e = owner.create_expense(
        ws["id"], amount_cents=123456, description="  Cinema  ", category="LAZER", icon_key="cinema"
    )
    assert set(e) == {
        "id",
        "workspace_id",
        "author",
        "amount_cents",
        "spent_at",
        "description",
        "category",
        "icon_key",
        "created_at",
        "updated_at",
    }
    assert e["amount_cents"] == 123456
    assert e["description"] == "Cinema"
    assert e["author"] == {"id": owner.id, "display_name": "Ana", "avatar_url": None}
    assert e["workspace_id"] == ws["id"]


def test_idempotency_same_key_twice(app, owner):
    ws = owner.create_workspace()
    headers = {"Idempotency-Key": "abc-123"}
    first = owner.post(f"/api/v1/workspaces/{ws['id']}/expenses", json=expense_body(), headers=headers)
    second = owner.post(f"/api/v1/workspaces/{ws['id']}/expenses", json=expense_body(), headers=headers)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.get_json()["id"] == second.get_json()["id"]
    with app.app_context():
        assert db.session.query(Expense).count() == 1


def test_idempotency_key_is_per_author(owner, partner, shared):
    headers = {"Idempotency-Key": "same-key"}
    a = owner.create_expense(shared["id"], headers=headers)
    b = partner.create_expense(shared["id"], headers=headers)
    assert a["id"] != b["id"]


def test_idempotency_different_keys(owner):
    ws = owner.create_workspace()
    a = owner.create_expense(ws["id"], headers={"Idempotency-Key": "k1"})
    b = owner.create_expense(ws["id"], headers={"Idempotency-Key": "k2"})
    assert a["id"] != b["id"]


def test_idempotency_key_reused_in_other_workspace(owner):
    ws1 = owner.create_workspace("A")
    ws2 = owner.create_workspace("B")
    owner.create_expense(ws1["id"], headers={"Idempotency-Key": "k"})
    r = owner.post(f"/api/v1/workspaces/{ws2['id']}/expenses", json=expense_body(), headers={"Idempotency-Key": "k"})
    assert r.status_code == 409


def test_idempotency_key_too_long(owner):
    ws = owner.create_workspace()
    r = owner.post(
        f"/api/v1/workspaces/{ws['id']}/expenses", json=expense_body(), headers={"Idempotency-Key": "k" * 129}
    )
    assert r.status_code == 400


def test_patch_expense_partial(owner, partner, shared):
    e = owner.create_expense(shared["id"], amount_cents=1000, category="LAZER", icon_key="bar")
    # o parceiro edita o gasto da dona (controle compartilhado)
    r = partner.patch(f"/api/v1/expenses/{e['id']}", json={"amount_cents": 2500, "icon_key": None})
    assert r.status_code == 200
    body = r.get_json()
    assert body["amount_cents"] == 2500
    assert body["icon_key"] is None
    assert body["description"] == e["description"]
    assert body["author"]["id"] == owner.id  # autor não muda
    assert body["updated_at"] >= e["updated_at"]


def test_patch_validates(owner):
    ws = owner.create_workspace()
    e = owner.create_expense(ws["id"])
    r = owner.patch(f"/api/v1/expenses/{e['id']}", json={"amount_cents": 0, "description": "x" * 101})
    assert r.status_code == 400
    assert set(r.get_json()["error"]["fields"]) == {"amount_cents", "description"}


def test_delete_is_soft(app, owner):
    ws = owner.create_workspace()
    e = owner.create_expense(ws["id"])
    assert owner.delete(f"/api/v1/expenses/{e['id']}").status_code == 204
    assert owner.get(f"/api/v1/workspaces/{ws['id']}/expenses").get_json()["items"] == []
    assert owner.delete(f"/api/v1/expenses/{e['id']}").status_code == 404
    assert owner.patch(f"/api/v1/expenses/{e['id']}", json={"amount_cents": 5}).status_code == 404
    with app.app_context():
        row = db.session.get(Expense, uuid.UUID(e["id"]))
        assert row is not None and row.deleted_at is not None


def test_unknown_expense_404(owner):
    assert owner.patch(f"/api/v1/expenses/{uuid.uuid4()}", json={}).status_code == 404


def _list(api, ws_id, query=""):
    r = api.get(f"/api/v1/workspaces/{ws_id}/expenses?{query}")
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def test_list_order_and_totals(owner):
    ws = owner.create_workspace()
    old = owner.create_expense(ws["id"], spent_at="2026-01-10", amount_cents=100)
    new1 = owner.create_expense(ws["id"], spent_at="2026-03-01", amount_cents=200)
    new2 = owner.create_expense(ws["id"], spent_at="2026-03-01", amount_cents=300)
    body = _list(owner, ws["id"])
    assert [e["id"] for e in body["items"]] == [new2["id"], new1["id"], old["id"]]
    assert body["total_count"] == 3
    assert body["total_cents"] == 600
    assert body["next_offset"] is None


def test_list_pagination(owner):
    ws = owner.create_workspace()
    for i in range(5):
        owner.create_expense(ws["id"], amount_cents=100 + i)
    page1 = _list(owner, ws["id"], "limit=2")
    assert len(page1["items"]) == 2 and page1["next_offset"] == 2
    assert page1["total_count"] == 5 and page1["total_cents"] == 510  # totais de tudo
    page3 = _list(owner, ws["id"], "limit=2&offset=4")
    assert len(page3["items"]) == 1 and page3["next_offset"] is None
    seen = [e["id"] for p in (page1, _list(owner, ws["id"], "limit=2&offset=2"), page3) for e in p["items"]]
    assert len(set(seen)) == 5


def test_list_filters(owner, partner, shared):
    wid = shared["id"]
    owner.create_expense(
        wid, description="Mercado Extra", category="ALIMENTACAO", amount_cents=5000, spent_at="2026-02-10"
    )
    owner.create_expense(
        wid, description="Cinema", category="LAZER", icon_key="cinema", amount_cents=3000, spent_at="2026-02-15"
    )
    partner.create_expense(
        wid, description="Uber pro mercado", category="TRANSPORTE", amount_cents=1500, spent_at="2026-03-01"
    )
    partner.create_expense(
        wid, description="100% off_promo", category="COMPRAS_ONLINE", amount_cents=999, spent_at="2026-03-02"
    )

    def descs(query):
        return sorted(e["description"] for e in _list(owner, wid, query)["items"])

    assert descs("q=MERCADO") == ["Mercado Extra", "Uber pro mercado"]
    assert descs("q=%25") == ["100% off_promo"]  # % literal, não curinga
    assert descs("q=_") == ["100% off_promo"]
    assert descs("category=LAZER,TRANSPORTE") == ["Cinema", "Uber pro mercado"]
    assert descs(f"author_id={partner.id}") == ["100% off_promo", "Uber pro mercado"]
    assert descs("date_from=2026-02-15&date_to=2026-03-01") == ["Cinema", "Uber pro mercado"]
    assert descs("amount_min=1500&amount_max=3000") == ["Cinema", "Uber pro mercado"]
    body = _list(owner, wid, "q=mercado&amount_min=2000")
    assert body["total_count"] == 1 and body["total_cents"] == 5000


def test_future_date_limit(owner):
    ws = owner.create_workspace()
    owner.create_expense(ws["id"], spent_at=days_from_today(31))
    owner.create_expense(ws["id"], expect=400, spent_at=days_from_today(32))

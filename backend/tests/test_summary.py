from app.timeutil import month_bounds, shift_month, today

from .conftest import join, login


def test_monthly_sums_exclude_deleted_and_other_months(owner, partner, shared):
    wid = shared["id"]
    owner.create_expense(wid, amount_cents=1050, spent_at="2026-10-01", category="ALIMENTACAO")
    owner.create_expense(wid, amount_cents=2000, spent_at="2026-10-31", category="LAZER")
    partner.create_expense(wid, amount_cents=999, spent_at="2026-10-15", category="ALIMENTACAO")
    deleted = partner.create_expense(wid, amount_cents=100000, spent_at="2026-10-20", category="PET")
    owner.delete(f"/api/v1/expenses/{deleted['id']}")
    owner.create_expense(wid, amount_cents=7777, spent_at="2026-09-30")  # mês anterior
    owner.create_expense(wid, amount_cents=8888, spent_at="2026-11-01")  # mês seguinte

    s = owner.get(f"/api/v1/workspaces/{wid}/summary?month=2026-10").get_json()
    assert s["month"] == "2026-10"
    assert s["total_cents"] == 1050 + 2000 + 999
    assert s["count"] == 3
    assert s["by_category"] == [
        {"category": "ALIMENTACAO", "total_cents": 2049, "count": 2},
        {"category": "LAZER", "total_cents": 2000, "count": 1},
    ]
    assert s["by_author"] == [
        {"user_id": owner.id, "display_name": "Ana", "total_cents": 3050, "count": 2},
        {"user_id": partner.id, "display_name": "Bruno", "total_cents": 999, "count": 1},
    ]
    assert s["evolution"] == [
        {"month": "2026-05", "total_cents": 0},
        {"month": "2026-06", "total_cents": 0},
        {"month": "2026-07", "total_cents": 0},
        {"month": "2026-08", "total_cents": 0},
        {"month": "2026-09", "total_cents": 7777},
        {"month": "2026-10", "total_cents": 4049},
    ]
    # o total do ambiente bate com o resumo
    ws = owner.get(f"/api/v1/workspaces/{wid}?month=2026-10").get_json()
    assert ws["month_total_cents"] == 4049
    listed = owner.get("/api/v1/workspaces?month=2026-10").get_json()["items"][0]
    assert listed["month_total_cents"] == 4049


def test_summary_includes_zero_members_and_ex_members(client, owner, partner, shared):
    wid = shared["id"]
    ex = login(client, "Ex")
    join(owner, ex, wid, "EDITOR")
    ex.create_expense(wid, amount_cents=500, spent_at="2026-10-05")
    owner.delete(f"/api/v1/workspaces/{wid}/members/{ex.id}")
    s = owner.get(f"/api/v1/workspaces/{wid}/summary?month=2026-10").get_json()
    assert s["by_author"] == [
        {"user_id": owner.id, "display_name": "Ana", "total_cents": 0, "count": 0},
        {"user_id": partner.id, "display_name": "Bruno", "total_cents": 0, "count": 0},
        {"user_id": ex.id, "display_name": "Ex", "total_cents": 500, "count": 1},
    ]
    assert s["total_cents"] == 500


def test_summary_empty_month(owner):
    ws = owner.create_workspace()
    s = owner.get(f"/api/v1/workspaces/{ws['id']}/summary?month=2020-01").get_json()
    assert s["total_cents"] == 0 and s["count"] == 0 and s["by_category"] == []
    assert [e["month"] for e in s["evolution"]] == ["2019-08", "2019-09", "2019-10", "2019-11", "2019-12", "2020-01"]


def test_summary_default_month_is_today_sao_paulo(owner):
    ws = owner.create_workspace()
    owner.create_expense(ws["id"], amount_cents=4321)
    t = today()
    s = owner.get(f"/api/v1/workspaces/{ws['id']}/summary").get_json()
    assert s["month"] == f"{t.year:04d}-{t.month:02d}"
    assert s["total_cents"] == 4321
    assert owner.get(f"/api/v1/workspaces/{ws['id']}").get_json()["month_total_cents"] == 4321


def test_large_values_no_overflow(owner):
    ws = owner.create_workspace()
    for _ in range(3):
        owner.create_expense(ws["id"], amount_cents=10_000_000_000, spent_at="2026-10-10")
    s = owner.get(f"/api/v1/workspaces/{ws['id']}/summary?month=2026-10").get_json()
    assert s["total_cents"] == 30_000_000_000


def test_month_helpers():
    assert month_bounds(2026, 12)[1].isoformat() == "2027-01-01"
    assert shift_month(2026, 1, -1) == (2025, 12)
    assert shift_month(2026, 3, -5) == (2025, 10)

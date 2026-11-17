"""Itens da revisão de AppSec: entradas extremas, idempotência após exclusão,
limites de requisição, cache dos certificados do Google."""

import pytest

from app import security
from app.extensions import limiter

from .conftest import expense_body, login, make_app

# --- entradas extremas nunca geram 500 ----------------------------------------------

EDGE_QUERIES = [
    "month=0000-01",
    "month=0001-01",
    "month=1999-12",
    "month=9999-12",
    "month=9998-12",
    "month=99999-01",
    "month=2026-00",
    "month=%00",
    "offset=1000001",
    "offset=99999999999999999999999",
    "limit=99999999999999999999999",
    "amount_min=10000000001",
    "amount_max=99999999999999999999999",
    "amount_min=-1",
    "date_from=9999-12-31",
    "date_to=0001-01-01",
    "date_from=%F0%9F%8D%95",
    "q=" + "%25" * 50,
    "q=" + "a" * 101,
    "category=,,,",
    "author_id=00000000-0000-0000-0000-000000000000",
]


@pytest.mark.parametrize("query", EDGE_QUERIES)
def test_edge_queries_never_500(owner, query):
    ws = owner.create_workspace()
    for path in ("expenses", "summary"):
        r = owner.get(f"/api/v1/workspaces/{ws['id']}/{path}?{query}")
        assert r.status_code < 500, (path, query, r.get_json())
    for path in ("/api/v1/workspaces", f"/api/v1/workspaces/{ws['id']}"):
        assert owner.get(f"{path}?{query}").status_code < 500


@pytest.mark.parametrize(
    "query,field",
    [
        ("month=1999-12", "month"),
        ("month=9999-01", "month"),
        ("offset=1000001", "offset"),
        ("amount_min=10000000001", "amount_min"),
        ("amount_max=10000000001", "amount_max"),
    ],
)
def test_edge_queries_are_400(owner, query, field):
    ws = owner.create_workspace()
    path = "summary" if field == "month" else "expenses"
    r = owner.get(f"/api/v1/workspaces/{ws['id']}/{path}?{query}")
    assert r.status_code == 400
    assert field in r.get_json()["error"]["fields"]


@pytest.mark.parametrize("query", ["month=2000-01", "month=9998-12", "offset=1000000", "amount_max=10000000000"])
def test_edge_queries_upper_bounds_accepted(owner, query):
    ws = owner.create_workspace()
    path = "summary" if query.startswith("month") else "expenses"
    assert owner.get(f"/api/v1/workspaces/{ws['id']}/{path}?{query}").status_code == 200


# --- idempotência ---------------------------------------------------------------------


def test_idempotent_replay_of_deleted_expense_conflicts(owner):
    ws = owner.create_workspace()
    headers = {"Idempotency-Key": "apagado"}
    e = owner.create_expense(ws["id"], headers=headers)
    owner.delete(f"/api/v1/expenses/{e['id']}")
    r = owner.post(f"/api/v1/workspaces/{ws['id']}/expenses", json=expense_body(), headers=headers)
    assert r.status_code == 409
    assert r.get_json()["error"]["code"] == "idempotency_conflict"


# --- limites de requisição ------------------------------------------------------------


@pytest.fixture
def limited_app():
    app = make_app(RATELIMIT_ENABLED=True)
    limiter.reset()
    yield app
    limiter.reset()


def test_write_limit_per_user(limited_app):
    c = limited_app.test_client()
    a, b = login(c), login(c)
    ws_a = a.create_workspace()
    ws_b = b.create_workspace()
    codes = [a.post(f"/api/v1/workspaces/{ws_a['id']}/expenses", json=expense_body()).status_code for _ in range(60)]
    assert codes == [201] * 60
    r = a.post(f"/api/v1/workspaces/{ws_a['id']}/expenses", json=expense_body())
    assert r.status_code == 429
    assert r.get_json()["error"]["code"] == "rate_limited"
    # o limite é por usuário: o outro (mesmo IP) continua escrevendo
    assert b.post(f"/api/v1/workspaces/{ws_b['id']}/expenses", json=expense_body()).status_code == 201


def test_default_limit_applies_to_reads(limited_app):
    c = limited_app.test_client()
    a = login(c)
    codes = [a.get("/api/v1/me").status_code for _ in range(301)]
    assert codes[:300] == [200] * 300
    assert codes[300] == 429


def test_health_is_exempt(limited_app):
    c = limited_app.test_client()
    assert all(c.get("/health").status_code == 200 for _ in range(320))
    assert all(c.get("/api/v1/health").status_code == 200 for _ in range(320))


def test_rate_limit_key(app):
    with app.test_request_context(headers={"Authorization": "Bearer lixo"}):
        assert security.rate_limit_key().startswith("ip:")
    with app.test_request_context():
        assert security.rate_limit_key().startswith("ip:")


# --- Google: cache dos certificados ---------------------------------------------------


class _FakeResponse:
    status = 200
    headers = {"cache-control": "public, max-age=600"}  # noqa: RUF012
    data = b'{"kid1": "-----BEGIN CERTIFICATE-----\\nMIIB\\n-----END CERTIFICATE-----\\n"}'


def test_google_certs_are_cached_with_timeout():
    calls = []
    transport = security._CachingGoogleRequest()

    def fake_inner(url, method="GET", body=None, headers=None, timeout=None, **kw):
        calls.append((url, timeout))
        return _FakeResponse()

    transport._inner = fake_inner
    url = "https://www.googleapis.com/oauth2/v1/certs"
    first = transport(url, method="GET")
    second = transport(url, method="GET")
    assert first is second
    assert calls == [(url, 10)]
    transport(url, method="POST", body=b"x")  # POST nunca usa cache
    assert len(calls) == 2


def test_google_request_is_singleton():
    assert security.google_request() is security.google_request()

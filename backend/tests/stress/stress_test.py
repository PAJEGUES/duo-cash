"""Teste de carga e concorrência do DuoCash contra uma API rodando.

Precisa do login de desenvolvimento (DEV_LOGIN_ENABLED=1), então NUNCA rode em produção.
Recomenda-se subir a API com RATELIMIT_DISABLED=1 para medir a aplicação e não o limitador.

    docker compose -f docker-compose.dev.yml up -d --build
    python tests/stress/stress_test.py --base-url http://localhost:8000 --expenses 400 --workers 32

Cenários:
  1. N lançamentos concorrentes de 2 usuários no mesmo ambiente;
  2. a mesma Idempotency-Key enviada 20x em paralelo -> exatamente 1 gasto;
  3. vários usuários aceitando o mesmo convite ao mesmo tempo -> exatamente 1 entra;
  3b. o mesmo refresh token 10x em paralelo -> exatamente 1 renova, o reuso revoga a família;
  4. leituras concorrentes (lista + resumo);
  5. confere se o total do resumo bate com a soma do que foi criado.
Sai com código 1 se alguma verificação falhar.
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import threading
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import httpx


def _pct(ordered: list[float], p: float) -> float:
    """Percentil pelo método do vizinho mais próximo (lista já ordenada)."""
    return ordered[min(len(ordered) - 1, round(p * (len(ordered) - 1)))]


class Stats:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.latency: dict[str, list[float]] = defaultdict(list)
        self.status: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self.errors: dict[str, int] = defaultdict(int)

    def record(self, op: str, seconds: float, status: int | None) -> None:
        with self.lock:
            self.latency[op].append(seconds * 1000)
            if status is None:
                self.errors[op] += 1
            else:
                self.status[op][status] += 1

    def report(self) -> None:
        print(f"\n{'operação':<22}{'n':>6}{'p50 ms':>9}{'p95 ms':>9}{'p99 ms':>9}{'max ms':>9}  status")
        for op, values in self.latency.items():
            ordered = sorted(values)

            codes = ", ".join(f"{k}:{v}" for k, v in sorted(self.status[op].items()))
            if self.errors[op]:
                codes += f", falhas_de_rede:{self.errors[op]}"
            print(
                f"{op:<22}{len(ordered):>6}{statistics.median(ordered):>9.1f}{_pct(ordered, 0.95):>9.1f}"
                f"{_pct(ordered, 0.99):>9.1f}{ordered[-1]:>9.1f}  {codes}"
            )


class Client:
    def __init__(self, base: str, stats: Stats, timeout: float = 30.0) -> None:
        self.base = base.rstrip("/") + "/api/v1"
        self.stats = stats
        self.http = httpx.Client(timeout=timeout, limits=httpx.Limits(max_connections=200))

    def call(self, op: str, method: str, path: str, token: str | None = None, **kw) -> httpx.Response | None:
        headers = kw.pop("headers", {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        start = time.perf_counter()
        try:
            resp = self.http.request(method, self.base + path, headers=headers, **kw)
        except httpx.HTTPError:
            self.stats.record(op, time.perf_counter() - start, None)
            return None
        self.stats.record(op, time.perf_counter() - start, resp.status_code)
        return resp

    def login(self, name: str) -> dict:
        email = f"stress-{uuid.uuid4().hex[:10]}@example.com"
        r = self.call("login", "POST", "/auth/dev", json={"email": email, "display_name": name})
        if r is None or r.status_code != 200:
            sys.exit(f"Falha no login de desenvolvimento ({r.status_code if r else 'rede'}). DEV_LOGIN_ENABLED=1?")
        return r.json()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--expenses", type=int, default=400, help="lançamentos concorrentes (2 usuários)")
    parser.add_argument("--workers", type=int, default=32, help="threads simultâneas")
    parser.add_argument("--idem-repeats", type=int, default=20)
    parser.add_argument("--invite-racers", type=int, default=10)
    parser.add_argument("--reads", type=int, default=200)
    args = parser.parse_args()

    stats = Stats()
    api = Client(args.base_url, stats)
    failures: list[str] = []

    def check(cond: bool, message: str) -> None:
        print(("  OK   " if cond else "  FALHA ") + message)
        if not cond:
            failures.append(message)

    r = api.call("health", "GET", "/health")
    if r is None or r.status_code != 200:
        print("API fora do ar em", args.base_url)
        return 1

    ana, bruno = api.login("Ana Stress"), api.login("Bruno Stress")
    ta, tb = ana["access_token"], bruno["access_token"]
    ws = api.call("workspace", "POST", "/workspaces", ta, json={"name": "Stress"}).json()
    wid = ws["id"]
    inv = api.call("invite", "POST", f"/workspaces/{wid}/invites", ta, json={"role": "EDITOR"}).json()
    api.call("accept", "POST", f"/invites/{inv['token']}/accept", tb)
    today = date.today().replace(day=1).isoformat()  # sempre dentro do mês corrente e do limite de data
    month = today[:7]

    # 1. lançamentos concorrentes ------------------------------------------------------
    print(f"\n[1] {args.expenses} lançamentos concorrentes de 2 usuários ({args.workers} threads)")
    created: list[int] = []
    created_lock = threading.Lock()

    def create(i: int) -> None:
        token = ta if i % 2 == 0 else tb
        amount = random.randint(1, 500_000)
        body = {
            "amount_cents": amount,
            "spent_at": today,
            "description": f"Gasto de carga {i}",
            "category": random.choice(["ALIMENTACAO", "LAZER", "TRANSPORTE", "PET", "BOLETOS"]),
        }
        resp = api.call(
            "create_expense",
            "POST",
            f"/workspaces/{wid}/expenses",
            token,
            json=body,
            headers={"Idempotency-Key": uuid.uuid4().hex},
        )
        if resp is not None and resp.status_code == 201:
            with created_lock:
                created.append(amount)

    t0 = time.perf_counter()
    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(create, range(args.expenses)))
    elapsed = time.perf_counter() - t0
    print(f"  {len(created)} criados em {elapsed:.2f}s ({len(created) / elapsed:.0f} req/s)")
    check(len(created) == args.expenses, f"todos os {args.expenses} lançamentos criados com 201")

    # 2. mesma Idempotency-Key em paralelo ---------------------------------------------
    print(f"\n[2] mesma Idempotency-Key {args.idem_repeats}x em paralelo")
    key = f"idem-{uuid.uuid4().hex}"
    idem_body = {"amount_cents": 4242, "spent_at": today, "description": "Toque duplo", "category": "LAZER"}
    barrier = threading.Barrier(args.idem_repeats)

    def idem(_: int):
        barrier.wait()
        return api.call(
            "idempotent_create",
            "POST",
            f"/workspaces/{wid}/expenses",
            ta,
            json=idem_body,
            headers={"Idempotency-Key": key},
        )

    with ThreadPoolExecutor(args.idem_repeats) as pool:
        results = [r for r in pool.map(idem, range(args.idem_repeats)) if r is not None]
    codes = [r.status_code for r in results]
    ids = {r.json()["id"] for r in results if r.status_code in (200, 201)}
    check(codes.count(201) == 1, f"exatamente um 201 (códigos: {sorted(codes)})")
    check(codes.count(200) == args.idem_repeats - 1, "os demais devolveram 200 com o mesmo gasto")
    check(len(ids) == 1, f"todas as respostas apontam para o mesmo id ({len(ids)} ids distintos)")
    listed = api.call("list_expenses", "GET", f"/workspaces/{wid}/expenses", ta, params={"q": "Toque duplo"}).json()
    check(listed["total_count"] == 1, f"só 1 gasto 'Toque duplo' no banco ({listed['total_count']})")
    created.append(4242)

    # 3. corrida no aceite do convite ------------------------------------------------
    print(f"\n[3] {args.invite_racers} usuários aceitando o mesmo convite ao mesmo tempo")
    racers = [api.login(f"Corredor {i}")["access_token"] for i in range(args.invite_racers)]
    race_inv = api.call("invite", "POST", f"/workspaces/{wid}/invites", ta, json={"role": "VIEWER"}).json()
    barrier = threading.Barrier(len(racers))

    def accept(token: str):
        barrier.wait()
        return api.call("accept_race", "POST", f"/invites/{race_inv['token']}/accept", token)

    with ThreadPoolExecutor(len(racers)) as pool:
        results = [r for r in pool.map(accept, racers) if r is not None]
    codes = sorted(r.status_code for r in results)
    check(codes.count(200) == 1, f"exatamente 1 aceite com sucesso (códigos: {codes})")
    check(codes.count(410) == len(racers) - 1, "os demais receberam 410 invite_used")
    members = api.call("members", "GET", f"/workspaces/{wid}/members", ta).json()["items"]
    check(len(members) == 3, f"ambiente ficou com 3 membros ({len(members)})")

    # 3b. corrida na renovação da sessão -------------------------------------------------
    print("\n[3b] o mesmo refresh token enviado 10x em paralelo")
    session = api.login("Refresh Stress")
    barrier = threading.Barrier(10)

    def refresh(_: int):
        barrier.wait()
        return api.call("refresh_race", "POST", "/auth/refresh", json={"refresh_token": session["refresh_token"]})

    with ThreadPoolExecutor(10) as pool:
        results = [r for r in pool.map(refresh, range(10)) if r is not None]
    codes = sorted(r.status_code for r in results)
    check(codes.count(200) == 1, f"exatamente 1 renovação aceita (códigos: {codes})")
    winner = next((r.json()["refresh_token"] for r in results if r.status_code == 200), None)
    if winner:
        again = api.call("refresh_race", "POST", "/auth/refresh", json={"refresh_token": winner})
        check(again is not None and again.status_code == 401, "reuso detectado: a família inteira foi revogada")

    # 4. leituras concorrentes ---------------------------------------------------------
    print(f"\n[4] {args.reads} leituras concorrentes (lista paginada + resumo)")

    def read(i: int) -> None:
        if i % 2:
            api.call("summary", "GET", f"/workspaces/{wid}/summary", ta if i % 4 == 1 else tb, params={"month": month})
        else:
            api.call(
                "list_expenses",
                "GET",
                f"/workspaces/{wid}/expenses",
                tb,
                params={"limit": 50, "offset": random.randint(0, args.expenses)},
            )

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(read, range(args.reads)))

    # 5. consistência dos totais -------------------------------------------------------
    print("\n[5] consistência dos totais")
    summary = api.call("summary", "GET", f"/workspaces/{wid}/summary", ta, params={"month": month}).json()
    expected = sum(created)
    check(summary["total_cents"] == expected, f"total do resumo {summary['total_cents']} == soma criada {expected}")
    check(summary["count"] == len(created), f"quantidade {summary['count']} == {len(created)}")
    by_author = sum(a["total_cents"] for a in summary["by_author"])
    by_cat = sum(c["total_cents"] for c in summary["by_category"])
    check(by_author == expected and by_cat == expected, "por pessoa e por categoria somam o total")
    listing = api.call("list_expenses", "GET", f"/workspaces/{wid}/expenses", ta, params={"limit": 1}).json()
    check(listing["total_cents"] == expected, "total da busca sem filtro bate com o resumo")

    stats.report()
    unexpected = sum(
        n
        for op, codes in stats.status.items()
        for code, n in codes.items()
        if code >= 500 or (code >= 400 and op not in ("accept_race", "refresh_race"))
    ) + sum(stats.errors.values())
    print(f"\nrequisições com erro inesperado (5xx, 4xx fora da corrida, falhas de rede): {unexpected}")
    check(unexpected == 0, "nenhum erro inesperado")

    print("\nRESULTADO:", "PASSOU" if not failures else f"FALHOU ({len(failures)} verificações)")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())

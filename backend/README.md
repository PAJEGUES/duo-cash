# DuoCash API

API REST do DuoCash em Flask + SQLAlchemy 2 + PostgreSQL. Contrato: base `/api/v1`, JSON em snake_case,
erros sempre no formato `{"error": {"code": "...", "message": "..."}}`.

## Rodar localmente com Docker (recomendado)

```bash
cd backend
docker compose -f docker-compose.dev.yml up --build
```

Sobe o Postgres e a API em `http://localhost:8000` (acessível só nesta máquina). As migrações rodam sozinhas
na subida. O login de desenvolvimento fica ligado:

```bash
curl -X POST http://localhost:8000/api/v1/auth/dev \
  -H "Content-Type: application/json" \
  -d '{"email": "ana@exemplo.com", "display_name": "Ana"}'
```

Para desligar: `docker compose -f docker-compose.dev.yml down` (acrescente `-v` para apagar o banco).

**Testar no celular pela rede local (Wi-Fi):** crie um `docker-compose.override.yml` ao lado (não versionar)
e suba com os dois arquivos. Só faça isso em rede confiável: o login de desenvolvimento fica exposto na rede.

```yaml
# docker-compose.override.yml
# services:
#   api:
#     ports: !override
#       - "0.0.0.0:8000:8000"
```

```bash
# docker compose -f docker-compose.dev.yml -f docker-compose.override.yml up --build
# no app, use http://<IP-do-computador>:8000
```

## Rodar sem Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export DATABASE_URL=sqlite:///duocash.db DEV_LOGIN_ENABLED=1 FLASK_APP=wsgi.py
flask db upgrade
flask run --port 8000
```

## Testes e verificações

```bash
pytest                                   # testes (SQLite em memória, não precisa de banco)
ruff check . && ruff format --check .    # lint
bandit -c pyproject.toml -r app          # análise de segurança
pip-audit -r requirements.txt            # dependências com vulnerabilidade conhecida
```

Teste de carga e concorrência (precisa da API rodando com o login de desenvolvimento; nunca em produção):

```bash
RATELIMIT_DISABLED=1 docker compose -f docker-compose.dev.yml up -d --build
python tests/stress/stress_test.py --base-url http://localhost:8000 --expenses 400 --workers 32
```

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `sqlite:///duocash.db` | URL do banco. `postgresql://...` usa o driver psycopg 3 |
| `SECRET_KEY` | — | Chave dos JWT. **Obrigatória, mínimo 32 caracteres** (a API não sobe sem ela) |
| `GOOGLE_CLIENT_IDS` | — | Client IDs OAuth aceitos no `aud`, separados por vírgula. O primeiro é o client **Web** (vai no `/config`) |
| `PUBLIC_BASE_URL` | `RENDER_EXTERNAL_URL` ou `http://localhost:8000` | Endereço público, usado no link do convite (`/convite/<token>`) |
| `INVITE_TTL_MINUTES` | `60` | Validade do convite |
| `DEV_LOGIN_ENABLED` | desligado | Liga `POST /auth/dev` (login sem Google). **Nunca em produção** |
| `ACCESS_TTL_MINUTES` | `15` | Validade do token de acesso |
| `REFRESH_TTL_DAYS` | `30` | Validade do token de renovação |
| `TRUST_PROXY` | desligado | Usa o `X-Forwarded-For` do proxy (Render ou Caddy) como IP do cliente |
| `RATELIMIT_DISABLED` | desligado | Desliga o limite de requisições (só para teste de carga) |
| `GUNICORN_WORKERS` / `GUNICORN_THREADS` | `2` / `4` | Processos e threads do gunicorn |

O "hoje" (mês padrão do resumo e limite de data futura dos gastos) é calculado no fuso `America/Sao_Paulo`.

## Limite de requisições

| Rota | Limite | Chave |
|---|---|---|
| Padrão (todas as rotas, exceto `/health`) | 300/min | usuário (token válido) ou IP |
| `POST /workspaces`, `POST /workspaces/{id}/expenses` | 60/min | usuário |
| `POST /auth/google`, `POST /auth/dev` | 20/min | IP |
| `POST /auth/refresh`, `POST /auth/logout` | 60/min | IP |
| `POST /workspaces/{id}/invites` | 20/min | usuário |
| `GET /invites/{token}`, `POST /invites/{token}/accept` | 30/min | usuário |

**Atenção:** o contador fica na memória de cada processo do gunicorn (`memory://`). Com 2 workers o limite
efetivo pode chegar a 2x o configurado, e ele zera quando o container reinicia. Para um limite exato seria
preciso um armazenamento compartilhado (ex.: Redis), o que não compensa no plano gratuito (no Render roda 1 worker, então o limite é exato até reiniciar).

## Sessões

- O access token dura 15 min; o refresh token, 30 dias, e **é de uso único**: cada `/auth/refresh` devolve um
  par novo e invalida o anterior. Reusar um refresh já usado derruba a sessão inteira (proteção contra roubo).
  O app precisa garantir **uma renovação por vez** (fila/single-flight).
- `POST /auth/logout` com `{"refresh_token": ...}` encerra a sessão do aparelho.
- `flask revoke-sessions <user_id>` encerra todas as sessões de um usuário (ex.: celular perdido).
- `flask purge-refresh-tokens` apaga tokens vencidos (também acontece sozinho, aos poucos, nos logins).

No servidor: aba **Shell** do serviço no Render (ou `docker compose exec api ...` numa VM): `flask purge-refresh-tokens`.

## Migrações

```bash
flask db migrate -m "descrição"   # gera uma nova versão a partir dos modelos
flask db upgrade                  # aplica
```

## Produção

Padrão gratuito: [`../render.yaml`](../render.yaml) (API no Render) + PostgreSQL no Neon. Passo a passo em
[`../docs/deploy.md`](../docs/deploy.md).

Alternativa com VM própria: pasta [`../deploy`](../deploy) com `docker-compose.yml` (Postgres + API + Caddy com
HTTPS automático), `Caddyfile`, `.env.example` e `setup-vm.sh` para preparar uma VM Debian 12.

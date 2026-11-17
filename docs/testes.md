# Plano de testes 360° do DuoCash

Este plano cobre o app (React Native) e a API (Flask + PostgreSQL). Para cada tipo de teste há o cenário prático, se ele é automatizado ou manual e a ferramenta usada.

Legenda da coluna **Status**: ✅ já implementado e rodando · 🟡 roteiro manual definido · ⏳ planejado.

## Como rodar os testes automatizados

```bash
# App
cd mobile
npm test            # Jest (unitários e cliente da API)
npm run typecheck   # TypeScript
npm run lint        # ESLint

# API
cd backend
pytest              # unitários, integração, validação de dados e segurança
ruff check .        # lint
bandit -r app       # análise estática de segurança
pip-audit -r requirements.txt   # dependências vulneráveis

# Estresse (com a API rodando)
python tests/stress/stress_test.py --base-url http://localhost:8000
```

O GitHub Actions roda os testes da API e do app a cada push e pull request.

## 1. Testes unitários

| Cenário | Abordagem | Ferramenta | Status |
|---|---|---|---|
| Conversão do valor digitado para centavos (`"86,00"` → `8600`), sem `float` | Automatizado | Jest | ✅ |
| Formatação de moeda (`123456` → `R$ 1.234,56`) | Automatizado | Jest | ✅ |
| Limite de 100 caracteres na descrição (emoji conta como 1) | Automatizado | Jest + PyTest | ✅ |
| Datas: mês anterior/seguinte, fevereiro em ano bissexto, "hoje"/"ontem" | Automatizado | Jest | ✅ |
| Leitura do QR Code: aceita só `duocash://join/<token>` e `https://.../convite/<token>` | Automatizado | Jest | ✅ |
| Endereço do servidor: só `https` em produção | Automatizado | Jest | ✅ |
| Soma do mês ignora gastos excluídos | Automatizado | PyTest | ✅ |
| Regras de permissão (Dono / Controle total / Somente leitura) | Automatizado | PyTest | ✅ |
| Hash do token do convite (o banco nunca guarda o token puro) | Automatizado | PyTest | ✅ |

## 2. Testes de integração

| Cenário | Abordagem | Ferramenta | Status |
|---|---|---|---|
| Login Google → usuário criado → tokens do app emitidos (Google simulado) | Automatizado | PyTest | ✅ |
| Renovação de sessão (refresh) com rotação: token antigo é recusado e reuso derruba a sessão inteira | Automatizado | PyTest + Jest | ✅ |
| Logout revoga a sessão no servidor | Automatizado | PyTest | ✅ |
| Ambiente arquivado fica somente leitura (409) | Automatizado | PyTest | ✅ |
| Várias requisições com token vencido fazem **uma** renovação só | Automatizado | Jest | ✅ |
| Criar ambiente → convidar → aceitar → lançar gasto → ver no resumo | Automatizado | PyTest | ✅ |
| Migrations do banco aplicadas do zero no PostgreSQL 15 | Automatizado | Alembic + Docker | ✅ |

## 3. Testes funcionais

| Cenário | Abordagem | Ferramenta | Status |
|---|---|---|---|
| Lançar gasto de R$ 86,00 em Lazer com ícone de cinema e conferir no extrato | Manual | Celular Android | 🟡 |
| Filtrar extrato por categoria + autor + faixa de valor e conferir o total | Manual | Celular Android | 🟡 |
| Navegar pelos meses no resumo e conferir gráfico de evolução | Manual | Celular Android | 🟡 |
| Contrato da API: formatos de resposta e códigos de erro | Automatizado | PyTest | ✅ |

## 4. Testes ponta a ponta (E2E)

| Cenário | Abordagem | Ferramenta | Status |
|---|---|---|---|
| Fluxo do casal: pessoa A cria "Casa", gera QR, pessoa B lê com a câmera, os dois lançam gastos, os dois veem o mesmo total | Manual (2 celulares) | APK + roteiro abaixo | 🟡 |
| Mesmo fluxo automatizado em emulador | Automatizado | Maestro | ⏳ |

**Roteiro manual com 2 celulares**
1. Celular A: entrar com Google, criar ambiente "Casa".
2. Celular A: aba Convidar → "Controle total" → QR Code aparece.
3. Celular B: entrar com Google → "Recebi um convite" → apontar a câmera → "Entrar no ambiente".
4. Celular B: lançar "Mercado R$ 100,00 (Alimentação)". Celular A: puxar para atualizar → gasto aparece com a inicial de B.
5. Celular A: tentar ler o **mesmo** QR em um terceiro aparelho → deve dizer "Convite inválido" (uso único).
6. Celular A: Resumo → "Quem gastou quanto" mostra os dois.

## 5. Testes de regressão

| Cenário | Abordagem | Ferramenta | Status |
|---|---|---|---|
| Toda a suíte roda a cada push/PR antes de entrar na `main` | Automatizado | GitHub Actions | ✅ |
| Erro corrigido ganha um teste novo que reproduz o problema | Automatizado | PyTest / Jest | ✅ (regra do projeto) |
| Roteiro E2E manual repetido antes de cada APK novo | Manual | Roteiro da seção 4 | 🟡 |

## 6. Testes de aceitação (UAT)

| Cenário | Abordagem | Ferramenta | Status |
|---|---|---|---|
| Registrar um gasto em menos de 10 segundos (RNF02), cronometrado | Manual | Cronômetro | 🟡 |
| O casal usa o app por uma semana e diz se o resumo "bate" com a realidade | Manual | Revisão da sprint | 🟡 |
| Os textos, cores e a pessoa de cada gasto estão claros para os dois | Manual | Revisão da sprint | 🟡 |

## 7. Testes exploratórios

| Cenário | Abordagem | Ferramenta | Status |
|---|---|---|---|
| Duplo toque rápido em "Salvar gasto" | Manual | Celular | 🟡 (protegido por `Idempotency-Key`) |
| Lançar gasto em modo avião e religar a internet | Manual | Celular | 🟡 (nova tentativa automática) |
| Trocar de tela durante o envio, girar o celular, voltar do segundo plano | Manual | Celular | 🟡 |
| Modo escuro do Android ligado/desligado | Manual | Celular | 🟡 |
| Colar textos estranhos (emoji, 1000 caracteres, HTML) nos campos | Manual | Celular | 🟡 |

## 8. Testes de segurança

| Cenário | Abordagem | Ferramenta | Status |
|---|---|---|---|
| IDOR: usuário B tenta ler/editar/excluir ambiente, gasto ou convite de A pelo id → 404 | Automatizado | PyTest | ✅ |
| JWT adulterado (`alg: none`, assinatura errada, refresh usado como access) → 401 | Automatizado | PyTest | ✅ |
| Somente leitura tentando criar/editar gasto direto na API → 403 | Automatizado | PyTest | ✅ |
| Convite reaproveitado, expirado ou cancelado → 410 | Automatizado | PyTest | ✅ |
| Cabeçalhos de segurança HTTP presentes | Automatizado | PyTest | ✅ |
| Análise estática do código Python | Automatizado | Bandit | ✅ |
| Dependências com vulnerabilidade conhecida | Automatizado | pip-audit / npm audit | ✅ |
| Varredura dinâmica da API publicada | Automatizado | OWASP ZAP (baseline) | ⏳ |

## 9. Testes não funcionais (performance, carga e estresse)

| Cenário | Abordagem | Ferramenta | Status |
|---|---|---|---|
| Dois usuários lançando gastos em paralelo; totais do resumo batem com a soma | Automatizado | `tests/stress/stress_test.py` | ✅ |
| Mesma `Idempotency-Key` enviada 20× em paralelo → 1 gasto só | Automatizado | `stress_test.py` | ✅ |
| Mesmo refresh token enviado 10× em paralelo → só 1 renova, a sessão é revogada | Automatizado | `stress_test.py` | ✅ |
| Vários usuários aceitando o mesmo convite ao mesmo tempo → só 1 entra | Automatizado | `stress_test.py` | ✅ |
| Latência p50/p95 das rotas principais na VM pequena (1 GB) | Automatizado | `stress_test.py` (relatório) | ✅ |
| Carga sustentada por 10 min | Automatizado | Locust | ⏳ |

## 10. Tratamento de erros e resiliência

| Cenário | Abordagem | Ferramenta | Status |
|---|---|---|---|
| Sem internet: app mostra "Sem conexão" e tenta de novo (até 3×, com espera crescente) | Automatizado + manual | Jest + celular | ✅ |
| Servidor devolve HTML/500: app mostra mensagem genérica, sem detalhes internos | Automatizado | Jest | ✅ |
| Sessão expirada: app renova sozinho; se não der, volta para o login | Automatizado | Jest | ✅ |
| API nunca devolve stack trace; erro 500 tem mensagem genérica | Automatizado | PyTest | ✅ |
| JSON malformado, corpo grande demais, tipos errados → 400/413 | Automatizado | PyTest | ✅ |
| Banco reiniciando: API volta sozinha (`restart: unless-stopped` + healthcheck) | Manual | Docker | 🟡 |

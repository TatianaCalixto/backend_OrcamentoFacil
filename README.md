# OrçaFácil — Backend

App de controle financeiro pessoal. Este repositório concentra o **backend (FastAPI)**, o **painel web (Streamlit)**, os **scripts de devops** e a **documentação técnica** do projeto.

> O app mobile (Flutter) vive em [frontend_OrcamentoFacil](https://github.com/TatianaCalixto/frontend_OrcamentoFacil).

🧭 Projeto desenvolvido com um fluxo de **documentação viva guiando a execução por sprints rastreáveis**.


## Como este projeto foi construído

Este projeto seguiu um fluxo de **documentação viva guiando a execução por
sprints**: a documentação define o *quê* e os critérios de pronto, e a
implementação avança sprint a sprint, com **testes obrigatórios** e
**rastreabilidade** de cada módulo até a sprint que o originou.

Estes projetos são desenvolvidos em **parceria com IA**: a arquitetura, os critérios
e a documentação são definidos por mim; a IA executa sob essa direção, sprint a
sprint. O método importa mais que a ferramenta.

O detalhamento da metodologia e o plano operacional completo ficam fora deste
repositório.

## Estrutura

```
backend_OrcamentoFacil/
├── backend/   # API FastAPI + SQLAlchemy + Alembic
├── panel/     # Painel web Streamlit
├── scripts/   # Utilitários de devops / migração / seed
└── docs/      # Documentação técnica do projeto
```

## Stack

- **Python** 3.12+
- **FastAPI**, **SQLAlchemy** 2, **Alembic**, **Pydantic** v2, **Pydantic-Settings**
- **PostgreSQL 16** (via Docker Compose em dev; Supabase ou similar em prod)
- **JWT** access + refresh (passlib[bcrypt] + python-jose)
- **slowapi** para rate limiting
- **pytest** + **pytest-asyncio** + **pytest-cov** + **httpx** para testes
- **Ruff** + **Black** para lint/format
- **Streamlit** + **Plotly** + **pandas** + **openpyxl** para o painel web

## Módulos da API

| Módulo | Endpoints | Sprint |
|---|---|---|
| `/auth` | register, login, refresh | 2, 10 |
| `/users` | me | 2 |
| `/accounts` | CRUD | 3 |
| `/categories` | CRUD + seed de 8 padrão no register | 4 |
| `/transactions` | CRUD + filtros + paginação | 5 |
| `/budgets` | CRUD com cálculo de status (ok/warning/critical) | 6 |
| `/goals` | CRUD com status automático | 7 |
| `/dashboard` | monthly-summary, category-breakdown, cashflow | 8 |
| `/imports` | POST /imports/csv (parser BR/US + categorização automática) | 9 |
| `/health` | smoke endpoint | 1 |

Docs interativos: `http://localhost:8000/docs` (Swagger UI) — descrições e tags organizadas.

## Decisões arquiteturais

- **Split em dois repos GitHub** (backend + frontend) em vez de monorepo — ver [docs/DECISOES.md](docs/DECISOES.md) (DEC-001).
- **Isolamento por usuário em todo CRUD**: queries sempre filtradas por `user_id`. Acesso cruzado retorna 404 (não 403) para não vazar existência.
- **Regra crítica de saldo** (Sprint 5): create soma; update reverte+aplica em ambas as contas; delete reverte. Garantia via `test_balance_regression_full_flow` em `backend/tests/test_balance_regression.py` — **se quebrar em qualquer sprint, parar e investigar**.
- **ENUM Postgres + StrEnum Python**: alembic não dropa types em downgrade — para reset local, `docker compose down -v`.
- **Coverage gate 80%** ativo em `pytest.ini` a partir da Sprint 10. Cobertura atual: ~96%.

## Requisitos

- **Python 3.12+** (testado em 3.12 e 3.14)
- **Docker Desktop** (Postgres local)
- **Git**

## Setup local

```bash
git clone https://github.com/TatianaCalixto/backend_OrcamentoFacil.git
cd backend_OrcamentoFacil
cp .env.example .env   # ajuste valores
```

Subir Postgres:
```bash
docker compose up -d
```

Criar venv e instalar:
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
```

Aplicar migrations:
```bash
alembic upgrade head
```

Rodar o backend:
```bash
uvicorn app.main:app --reload
# health: http://localhost:8000/health
# docs:   http://localhost:8000/docs
```

## Rodar o painel Streamlit

```bash
cd panel
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
streamlit run app.py
# abre em http://localhost:8501
```

Veja [panel/README.md](panel/README.md) para detalhes.

## Rodar testes

Backend:
```bash
cd backend
source .venv/Scripts/activate
pytest                          # cov >= 80% obrigatório
pytest --no-cov                 # sem gate de cobertura
pytest tests/test_balance_regression.py -v   # bateria crítica
```

Painel:
```bash
cd panel
source .venv/Scripts/activate
pytest tests/
```

Smoke contra ambiente real:
```bash
# contra local
ORCAFACIL_SMOKE_URL=http://localhost:8000 python scripts/smoke_prod.py
# contra prod
ORCAFACIL_SMOKE_URL=https://meu-deploy.com python scripts/smoke_prod.py
```

## Lint e formatação

```bash
cd backend
source .venv/Scripts/activate
ruff check .          # lint
ruff check . --fix    # autofix
black .               # formata
black --check .       # apenas confere
```

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda em todo push/PR:

1. `pip install -r backend/requirements.txt`
2. `ruff check .`
3. `black --check .`
4. `pytest` (com cov gate)

Service container `postgres:16-alpine` disponível para testes de integração.

O step **Security audit** roda antes do lint (ver "Segurança de dependências").

## Segurança de dependências

Duas camadas de varredura de CVE (Fase 3 / Sprint 20):

1. **Dependabot** ([`.github/dependabot.yml`](.github/dependabot.yml)) — varredura
   semanal de `backend/`, `panel/` e GitHub Actions; abre PRs de atualização e,
   com "Dependabot security updates" ligado, PRs de correção de vulnerabilidade.
2. **pip-audit no CI** ([`scripts/ci_pip_audit.py`](scripts/ci_pip_audit.py)) — gate
   obrigatório em todo push/PR, rodando `pip-audit` contra `requirements.txt`.

### Política de severidade

O `pip-audit` sozinho falha em qualquer vulnerabilidade. O wrapper
`scripts/ci_pip_audit.py` consulta a severidade na API pública do
[OSV](https://osv.dev) e aplica:

| Severidade (OSV) | Efeito no CI |
|---|---|
| **Critical / High** | ❌ Falha (build vermelho) |
| **Medium / Low** | ⚠️ Warning (build passa) |
| **Indeterminada** | ❌ Falha (fail-closed) |

### Como remediar uma falha

1. Veja na saída do step a dependência, o ID (GHSA/CVE) e a **fix version**.
2. Atualize a versão em `backend/requirements.txt` para a fix indicada e rode
   localmente:
   ```bash
   cd backend
   python ../scripts/ci_pip_audit.py -r requirements.txt
   ```
3. Se não houver correção e o risco for aceito (com justificativa), adicione a
   vuln à allowlist do pip-audit:
   ```bash
   pip-audit -r requirements.txt --ignore-vuln GHSA-xxxx-xxxx-xxxx
   ```
   (registre a justificativa na aba Decisões da planilha operacional).

## Deploy

> **Status:** Dockerfile pronto (Sprint 16-T01). Provisionamento Supabase/Railway/Render aguarda credenciais — ver IMP-001/002/003 na planilha operacional.

Build local da imagem:
```bash
cd backend
docker build -t orcafacil-backend:latest .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db \
  -e JWT_SECRET=trocar_em_producao \
  -e ENVIRONMENT=production \
  -e CORS_ORIGINS=https://meu-front.app,https://meu-painel.app \
  orcafacil-backend:latest
```

Dockerfile: multi-stage (builder + runtime enxuta), user não-root `app`, healthcheck via curl em `/health`, `uvicorn --workers 2`.

## Estrutura de pastas detalhada

```
backend/
├── app/
│   ├── __init__.py            # __version__
│   ├── main.py                # FastAPI() + middlewares + routers
│   ├── core/                  # config, errors, logging, ratelimit
│   ├── database/              # engine, session, Base
│   ├── auth/                  # JWT, deps, security, router
│   ├── users/                 # User model + router
│   ├── accounts/              # Account: model + schemas + service + router
│   ├── categories/            # Category: idem + seed.py
│   ├── transactions/          # Transaction: idem (regra crítica)
│   ├── budgets/               # Budget: idem (com status)
│   ├── goals/                 # Goal: idem (com status auto)
│   ├── dashboard/             # 3 endpoints de agregação
│   └── imports/               # CSV: parser + service + router
├── alembic/                   # migrations
├── tests/                     # pytest (220+ testes)
├── Dockerfile                 # produção
├── pytest.ini
├── pyproject.toml             # ruff + black + coverage
└── requirements.txt
panel/
├── app.py                     # entrada Streamlit (login)
├── api.py                     # wrapper requests
├── pages/                     # páginas Streamlit
├── tests/                     # smoke da API
├── requirements.txt
└── README.md
```

## Troubleshooting

| Sintoma | Causa provável | Como resolver |
|---|---|---|
| `docker compose up` falha com "cannot find docker_engine" | Docker Desktop não está rodando | Abrir Docker Desktop e aguardar daemon ficar disponível |
| `connection refused` ao psql | Postgres ainda subindo | `docker compose ps` e esperar `healthy` |
| `pip install` falha por SSL no Windows | Certificados desatualizados | `python -m pip install --upgrade pip certifi` |
| Porta 5432 já ocupada por outro Postgres do host | Conflito de porta | Mudar `POSTGRES_PORT` no `.env` (ex.: `POSTGRES_PORT=5433`) |
| Push GitHub dá 403 | Credencial cacheada de outra conta | Apagar `git:https://github.com` no Windows Credential Manager e refazer o push |
| `alembic upgrade head` falha com "type X already exists" | Volume Postgres tem ENUM órfão de testes anteriores | `docker compose down -v` reseta o volume |
| `bcrypt` quebra com erro `__about__` | bcrypt >= 4.1 incompatível com passlib 1.7.4 | Pin `bcrypt>=4.0,<4.1` (já no requirements.txt) |
| Rate limit 429 em desenvolvimento | Default de 10/min em /auth/* | Esperar o reset (1 minuto) ou rodar via test que reseta entre testes |

## Limitações conhecidas

- **Transferências entre contas** não modeladas explicitamente (workaround atual: dois lançamentos manuais).
- **Multi-moeda** não suportado (assume BRL).
- **Reservas/lançamentos futuros**: campo `is_recurring` no Transaction existe mas não há agendamento automático.
- **OFX/QIF**: import só suporta CSV.

## Roadmap futuro (pós-MVP)

- Transferências entre contas como entidade própria.
- Notificações push (FCM) quando budget passa de 80%/100%.
- Recurrent transactions com cron.
- Multi-currency.
- 2FA opcional.
- OAuth (Google) além do email/senha.

## Status do projeto

**MVP completo** em 1 dia (2026-05-23 → 2026-05-24, 17 sprints planejadas).

| Sprint | Conteúdo | Status |
|---|---|---|
| 0 | Setup + CI + Docker | ✓ |
| 1 | FastAPI core + Alembic + logging | ✓ |
| 2 | Auth JWT + /users/me | ✓ |
| 3 | CRUD Accounts | ✓ |
| 4 | CRUD Categories + seed | ✓ |
| 5 | CRUD Transactions + regra de saldo + regressão | ✓ |
| 6 | Budgets mensais com status | ✓ |
| 7 | Goals com status auto | ✓ |
| 8 | Dashboard backend (3 endpoints) | ✓ |
| 9 | Import CSV | ✓ |
| 10 | Hardening (CORS, rate limit, refresh, OpenAPI, cov 80%) | ✓ |
| 11 | Flutter setup + auth | ✓ |
| 12 | Flutter dashboard + transactions | ✓ |
| 13 | Flutter categorias/orçamento/metas | ⚠ em andamento (agente paralelo) |
| 14 | Flutter perfil + import CSV | ⚠ em andamento (agente paralelo) |
| 15 | Painel Streamlit | ✓ |
| 16 | Deploy + docs final | ✓ T01/T05/T06; ⚠ T02/T03/T04 bloqueados (IMP-001/002/003) |

O plano completo e a planilha operacional ficam fora do repositório.

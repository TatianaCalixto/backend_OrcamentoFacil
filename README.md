# OrçaFácil — Backend

App de controle financeiro pessoal. Este repositório concentra o **backend (FastAPI)**, o **painel web (Streamlit)**, os **scripts de devops** e a **documentação técnica** do projeto.

> O app mobile (Flutter) vive em [frontend_OrcamentoFacil](https://github.com/TatianaCalixto/frontend_OrcamentoFacil).

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
- **PostgreSQL 16** (via Docker Compose)
- **JWT** para autenticação (passlib[bcrypt] + python-jose)
- **pytest** + **pytest-asyncio** + **pytest-cov** + **httpx** para testes
- **Ruff** + **Black** para lint/format
- **Streamlit** para o painel web

## Requisitos

- **Python 3.12+**
- **Docker Desktop** (para Postgres local)
- **Git**

## Setup

### 1. Clonar e configurar variáveis de ambiente

```bash
git clone https://github.com/TatianaCalixto/backend_OrcamentoFacil.git
cd backend_OrcamentoFacil
cp .env.example .env   # edite valores conforme necessário
```

O arquivo `.env.example` documenta todas as variáveis (Postgres + variáveis do backend que entrarão em uso a partir da Sprint 1).

### 2. Subir o Postgres local

```bash
docker compose up -d
# verificar:
docker compose ps
```

Dados ficam num volume nomeado `orcafacil_pgdata` e persistem entre restarts.

Para derrubar: `docker compose down` (sem `-v`, preserva o volume).
Para zerar tudo (apaga dados): `docker compose down -v`.

### 3. Criar venv e instalar dependências do backend

```bash
cd backend
python -m venv .venv
# Windows (Git Bash):
source .venv/Scripts/activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

## Rodando o backend

> A aplicação FastAPI será criada na Sprint 1 (S01-T01). Por enquanto, apenas a infraestrutura de projeto está pronta.

A partir da Sprint 1:

```bash
cd backend
source .venv/Scripts/activate
uvicorn app.main:app --reload
# health check em http://localhost:8000/health
```

## Rodando os testes

```bash
cd backend
source .venv/Scripts/activate

# suite completa
pytest

# com coverage
pytest --cov=app --cov-report=term-missing

# apenas um arquivo
pytest tests/test_smoke.py -v
```

A configuração vive em [`backend/pytest.ini`](backend/pytest.ini): `asyncio_mode=auto`, `testpaths=tests`, `--strict-markers`. A meta de cobertura ≥ 80% será aplicada a partir da Sprint 10 (hardening).

## Lint e formatação

```bash
cd backend
source .venv/Scripts/activate

ruff check .          # lint
ruff check . --fix    # autofix
black .               # formata
black --check .       # apenas confere
```

Configuração em [`backend/pyproject.toml`](backend/pyproject.toml) (linha 100, target py312, regras `E/F/W/I/B/UP/SIM`).

## CI

Pipeline em [`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda em todo push e PR:

1. `pip install -r requirements.txt`
2. `ruff check .`
3. `black --check .`
4. `pytest`

Service container `postgres:16-alpine` já fica disponível para testes de integração.

## Troubleshooting

| Sintoma | Causa provável | Como resolver |
|---|---|---|
| `docker compose up` falha com "cannot find docker_engine" | Docker Desktop não está rodando | Abrir Docker Desktop e aguardar daemon ficar disponível |
| `connection refused` ao psql | Postgres ainda subindo (sem healthcheck pronto) | `docker compose ps` e esperar `healthy`; o healthcheck roda a cada 5s |
| `pip install` falha por SSL no Windows | Certificados desatualizados | `python -m pip install --upgrade pip certifi` |
| `ModuleNotFoundError` nos testes | venv não ativada ou pasta `app/` ainda não existe | Ativar venv; lembrar que `app/` é criada em S01-T01 |
| Porta 5432 já ocupada | Outro Postgres local rodando | Mudar `POSTGRES_PORT` no `.env` (ex.: `POSTGRES_PORT=5433`) |
| Push GitHub dá 403 | Credencial cacheada de outra conta | Apagar `git:https://github.com` no Windows Credential Manager e refazer o push |

## Status

Em desenvolvimento — **Sprint 0** (Setup do Projeto e Infraestrutura).

O plano de execução completo (17 sprints, 67 tarefas) é mantido fora do repositório, em planilha operacional privada.

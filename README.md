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
- **FastAPI**, **SQLAlchemy**, **Alembic**, **Pydantic v2**
- **PostgreSQL 16** (via Docker Compose)
- **JWT** para autenticação
- **pytest**, **pytest-asyncio**, **httpx** para testes (cobertura via `pytest --cov`)
- **Ruff** + **Black** para lint/format
- **Streamlit** para o painel web

## Requisitos

- Python 3.12+
- Docker Desktop (para Postgres local)
- Git

## Setup

> Documentação detalhada será adicionada na tarefa **S00-T06** ao final da Sprint 0.

```bash
git clone https://github.com/TatianaCalixto/backend_OrcamentoFacil.git
cd backend_OrcamentoFacil
cp .env.example .env   # disponível a partir de S00-T02
```

## Status

Em desenvolvimento — Sprint 0 (Setup do Projeto e Infraestrutura).

O plano de execução completo (17 sprints, 67 tarefas) é mantido fora do repositório, em planilha operacional privada.

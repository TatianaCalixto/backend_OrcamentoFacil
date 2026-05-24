# Arquitetura — OrçaFácil

## Visão geral

```
┌──────────────────┐         ┌──────────────────────┐
│  Mobile Flutter  │ ──HTTP─▶│                      │
│  (frontend repo) │         │                      │
└──────────────────┘         │   FastAPI Backend    │
                             │   (este repo)        │ ──SQL──▶ PostgreSQL
┌──────────────────┐         │                      │
│  Streamlit Panel │ ──HTTP─▶│  + Auth JWT          │
│  (panel/)        │         │  + Rate limit        │
└──────────────────┘         │  + CORS por env      │
                             └──────────────────────┘
```

## Camadas do backend

```
HTTP (FastAPI router) → Service (regras de negócio) → Repository (SQL) → SQLAlchemy → Postgres
                       ↑
                       └─ Pydantic schemas (entrada/saída)
```

- **Router**: declarativo, mapeia HTTP para chamadas de service. Tradução de exceções de domínio em HTTPException.
- **Service**: regras de negócio. Sempre recebe `user_id` e impõe isolamento. Levanta exceções de domínio (`OwnershipError`, `BudgetOwnershipError`, etc.).
- **Repository**: queries SQL puras. Métodos sempre filtrando por `user_id`. Sem regras de negócio.
- **Schemas**: validação de shape (Pydantic). Cross-validation (existência, ownership) fica no service.
- **Models**: ORM SQLAlchemy 2 com `Mapped`/`mapped_column` e naming convention explícita.

## Decisões importantes

### Isolamento por usuário
- Todas as queries de leitura/escrita filtram por `user_id`.
- Acesso a recurso de outro usuário retorna **404** (não 403/401) para não vazar existência.
- Garantido em testes para cada CRUD (`test_*_router.py` tem cenário "outro usuário 404").

### Regra crítica de saldo (Sprint 5)
- **Create**: `account.current_balance += signed(amount, type)`.
- **Update**:
  - Mesma conta: `delta = new_signed - old_signed`.
  - Mudou conta: reverte na antiga, aplica na nova.
- **Delete**: `account.current_balance -= signed(amount, type)`.
- Coberto por `test_balance_regression_full_flow` (cenário longo de 2 contas com 10+ operações).
- **Se quebrar**: PARAR, investigar, NÃO prosseguir.

### Status de Budget
- Calculado em runtime no GET (não persistido).
- Regra: `>100%` critical, `>80%` warning, senão ok.
- Soma considera apenas `EXPENSE` no intervalo `[primeiro_dia_mês, ultimo_dia_mês]`.

### Status de Goal
- Calculado em runtime no CREATE e em todo UPDATE (e persistido na tabela).
- Regra: `current_amount >= target_amount → completed`, senão `in_progress`.
- Reverte automaticamente quando current cai abaixo do target.

### Import CSV
- Parser tolerante: detecta delimitador (, ou ;), header pt/en com normalização NFKD (aceita acentos), datas ISO/BR, valores BR/US/R$.
- Sinal do valor define o tipo: `> 0` income, `< 0` expense.
- Categorização por keyword na descrição (UBER, IFOOD, NETFLIX, DROGARIA…), fallback "Outros".
- Saldo da conta atualizado em UMA gravação no fim (delta somado), num único commit.
- Linhas inválidas viram `errors[]` no payload de resposta sem abortar o batch.

### Logging e request_id
- Middleware `RequestIdMiddleware` gera (ou propaga) UUID por requisição.
- Toda resposta tem header `X-Request-ID`.
- Toda linha de log carrega `request_id` quando disponível.
- Em produção (`ENVIRONMENT=production|staging`): JSON. Em dev/test: texto.

### Rate limiting
- `slowapi` com chave por IP.
- 10/min em `/auth/register` e `/auth/login`.
- Outros endpoints sem limite explícito (ainda).

### Refresh tokens
- Access token: 60min (configurável via `JWT_EXPIRE_MINUTES`).
- Refresh token: 7d (configurável via `JWT_REFRESH_EXPIRE_MINUTES`).
- Claim `typ` distingue access/refresh; misuse cruzado retorna 401.

### CORS
- `Settings.cors_origins` parseado de `CORS_ORIGINS` (CSV ou JSON no env).
- Default seguro para dev (localhost). Em prod, configurar explicitamente.

## Modelo de dados

```
users (1) ─── (N) accounts
              └── (N) transactions ─── (N) categories
              
users (1) ─── (N) categories
users (1) ─── (N) budgets ─── (1) categories
users (1) ─── (N) goals
```

- FK `transactions.account_id` ON DELETE CASCADE.
- FK `transactions.category_id` ON DELETE RESTRICT (impede deletar categoria com lançamentos — exceto se não houver).
- FK `accounts.user_id`, `categories.user_id`, `budgets.user_id`, `goals.user_id` ON DELETE CASCADE.
- Unique compound em `budgets(user_id, category_id, month, year)`.
- Índices compostos em `transactions(user_id, date)` e `transactions(account_id, date)` para queries do dashboard.

## Testes

- **Unit**: schemas, security helpers, jwt, parser CSV.
- **Integration**: cada router via `TestClient(app)`. Banco SQLite in-memory com `StaticPool` (compartilhado entre sessions) + PRAGMA `foreign_keys=ON`.
- **Bateria de regressão**: `test_balance_regression.py` — cenário E2E longo.
- **Cobertura**: gate >= 80% global ativo em `pytest.ini`. Atual: 96.6%.

## CI

- GitHub Actions roda em todo push/PR.
- Ubuntu + Python 3.12 + service container `postgres:16-alpine`.
- Pipeline: install → ruff → black --check → pytest (com cov gate).

## Próximos passos (Sprint 16 + além)

- Provisionar Supabase (IMP-001) e deploy Railway/Render (IMP-002).
- Build APK Android assinado (IMP-003).
- Hardening adicional: 2FA, OAuth Google, audit log.
- Otimização: query do dashboard com window functions para cashflow.
- Multi-currency.

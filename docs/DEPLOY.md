# Deploy — OrçaFácil (Fase 3 / Sprint 22)

Runbook para colocar o OrçaFácil em produção pública. Agnóstico de provedor
onde possível; onde há escolha, listamos as opções avaliadas (decisão de
provedor pendente — ver planilha). **Nenhum segredo neste documento**: tokens,
senhas e URLs com credenciais vivem nos cofres de secrets dos provedores.

Arquitetura em produção:

```
[App Flutter (APK)] ──┐
                      ├──> [Backend FastAPI]  ──> [Postgres gerenciado]
[Painel Streamlit] ───┘         (Docker)            (Supabase/Neon)
```

> Estado: este runbook é o **groundwork** da Sprint 22. Os passos marcados com
> 🧑 exigem execução humana (criar conta, provisionar, configurar secrets). O
> agente preparou artefatos (Dockerfile, `.env.example`, `scripts/pg_backup.sh`,
> `scripts/smoke_prod.py`) mas não tem acesso aos provedores.

---

## 1. Postgres gerenciado (S22-T01)

Opções avaliadas: **Supabase** (tem backup nativo no free tier) ou **Neon**.

🧑 **Passos:**
1. Criar um projeto Postgres no provedor escolhido.
2. Copiar a connection string e montar a `DATABASE_URL` no formato do driver:
   `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME`.
3. Aplicar as migrations remotamente (a partir de `backend/`, com `DATABASE_URL`
   apontando para o banco gerenciado):
   ```bash
   cd backend
   DATABASE_URL="postgresql+psycopg://..." alembic upgrade head
   ```
4. Conferir que as tabelas foram criadas (`users`, `accounts`, `categories`,
   `transactions`, `budgets`, `goals`, `revoked_tokens`, `alembic_version`).
5. Atualizar `backend/.env.example` continua como referência; o valor real vai
   nos secrets do backend (passo 2).

---

## 2. Deploy do backend (S22-T02)

Opções avaliadas: **Render** ou **Railway**. Ambos sobem a imagem do
`backend/Dockerfile` (multi-stage, user não-root, healthcheck em `/health`,
`uvicorn --workers 2`).

🧑 **Passos:**
1. Conectar o repositório `backend_OrcamentoFacil` ao provedor, apontando o build
   para `backend/Dockerfile` (contexto: `backend/`).
2. Configurar as variáveis de ambiente (ver `backend/.env.example`):
   `DATABASE_URL`, `JWT_SECRET`, `ENVIRONMENT=production`, `CORS_ORIGINS`
   (incluir a URL do painel e do app), e opcionalmente `LOG_SHIPPING_*`.
3. Garantir que a porta exposta é `8000` e o healthcheck aponta para `/health`
   (ou `/healthz` para checagem profunda com DB).
4. Após o deploy, rodar o smoke contra a URL pública:
   ```bash
   ORCAFACIL_SMOKE_URL="https://SEU-BACKEND.onrender.com" python scripts/smoke_prod.py
   ```
   Deve sair com código 0 (8 checagens verdes). Confere o critério de aceitação.

---

## 3. Deploy do painel Streamlit (S22-T03)

Opção: **Streamlit Community Cloud** (gratuito) apontando para
`backend_OrcamentoFacil` → `panel/app.py`.

🧑 **Passos:**
1. Criar o app no Streamlit Cloud, repositório `backend_OrcamentoFacil`, arquivo
   principal `panel/app.py`, branch `main`.
2. Em *Advanced settings → Secrets / env*, definir:
   `ORCAFACIL_API_URL = "https://SEU-BACKEND.onrender.com"` (o painel lê essa env;
   default é `http://localhost:8000`).
3. Dependências saem de `panel/requirements.txt` automaticamente.
4. Validar login no painel contra o backend de produção.

---

## 4. APK release (S22-T04)

🧑 **Passos:**
1. Apontar o app para a URL de produção. O app lê `API_BASE_URL` do `.env`
   (asset, via flutter_dotenv). Para o release, ajustar `mobile/.env` (gitignored)
   com `API_BASE_URL=https://SEU-BACKEND.onrender.com` **ou** passar via
   `--dart-define` se preferir não versionar.
2. Gerar o APK assinado:
   ```bash
   cd mobile
   flutter build apk --release
   ```
   (Configurar `key.properties`/keystore conforme a doc do Flutter — keystore é
   segredo, fora do git.)
3. Smoke manual: instalar o APK em um emulador/dispositivo e validar login +
   uma transação contra produção.

---

## 5. Backup automatizado do Postgres (S22-T05)

Duas estratégias (use a que o provedor oferecer):

- **Backup nativo do Supabase** (free tier inclui backups automáticos com
  retenção limitada) — habilitar no painel do projeto.
- **Job próprio com `pg_dump`** — usar [`scripts/pg_backup.sh`](../scripts/pg_backup.sh)
  em um cron/scheduler:
  ```bash
  DATABASE_URL="postgresql+psycopg://..." BACKUP_DIR=/var/backups RETENTION_DAYS=7 \
    ./scripts/pg_backup.sh
  ```
  O script gera `orcafacil_<timestamp>.dump` (formato custom) e remove dumps mais
  antigos que `RETENTION_DAYS`.

🧑 **Validação por restore manual** (critério de aceitação):
```bash
# em um banco/scratch separado, NUNCA no de produção:
pg_restore --clean --no-owner --dbname="postgresql://user:pass@host:5432/scratch" \
  orcafacil_<timestamp>.dump
```
Conferir que as tabelas e dados voltam corretamente.

---

## 6. Checklist final (S22-T06)

- [ ] Postgres gerenciado provisionado e migrations aplicadas.
- [ ] Backend deployado; `/health` e `/healthz` respondem; smoke verde.
- [ ] Painel Streamlit no ar, autenticando contra o backend de produção.
- [ ] APK release gerado e validado em emulador.
- [ ] Backup automatizado configurado e **restore testado** manualmente.
- [ ] `/metrics` acessível (e, se exposto publicamente, considerar basic auth no proxy).
- [ ] URLs públicas registradas (aqui ou no cofre de secrets do time).

> Credenciais (DATABASE_URL, JWT_SECRET, tokens) **não** entram neste doc nem no
> git — apenas nos secrets dos provedores.

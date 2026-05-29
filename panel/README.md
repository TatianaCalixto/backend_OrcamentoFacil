# Painel Web — OrçaFácil

Painel Streamlit para visualização rica de relatórios financeiros, consumindo o backend OrçaFácil. Sprint 15.

## Setup

```bash
cd panel
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# ou: source .venv/bin/activate (macOS/Linux)
pip install -r requirements.txt
```

## Configurar URL do backend

```bash
# default: http://localhost:8000
export ORCAFACIL_API_URL=http://localhost:8000
```

(No Windows PowerShell: `$env:ORCAFACIL_API_URL = "http://localhost:8000"`.)

## Rodar

```bash
streamlit run app.py
```

Abre em `http://localhost:8501`.

## Páginas

- **Home (`app.py`)** — login (chama `POST /auth/login`), sessão guardada em `st.session_state`. Logout limpa estado.
- **Relatórios (`pages/1_Relatorios.py`)** — resumo mensal, breakdown por categoria (pizza), fluxo de caixa (linha). Filtros de mês/ano e date range.
- **Transações (`pages/2_Transacoes.py`)** — lista com filtros (data, conta, categoria, tipo, busca textual) e botões de **exportação CSV e XLSX**.
- **Contas (`pages/3_Contas.py`)** — CRUD de contas (listar, criar, editar, excluir).

## Smoke test manual

1. Subir backend local (`uvicorn app.main:app --reload` em `backend/` com `.env` apontando para um Postgres).
2. Registrar um usuário via `POST /auth/register` (ou via app Flutter).
3. Adicionar uma conta e algumas transações.
4. `streamlit run app.py`, fazer login, navegar pelas páginas.
5. Exportar CSV/XLSX e abrir.

### Smoke test manual — Contas

1. Subir backend e fazer login no painel.
2. Acessar a página **Contas** no menu lateral.
3. Expandir **"+ Nova conta"**, preencher nome `Teste S17`, tipo `Corrente`, saldo inicial `0,00` e clicar **Criar**.
4. Verificar que a conta `Teste S17` aparece na listagem após o rerun.
5. Expandir **"Editar conta"**, selecionar `Teste S17`, alterar o nome para `Teste S17 editado` e clicar **Salvar**.
6. Expandir **"Excluir conta"**, selecionar `Teste S17 editado`, marcar **Confirmo a exclusão** e clicar **Excluir**.
7. Confirmar que a conta sumiu da listagem.

## Notas

- A cache de `_fetch_all` em Transações tem TTL de 60s; force refresh re-rodando a página.
- Os relatórios sempre re-consultam o backend (sem cache) para refletir mudanças em tempo real.
- O painel não tem CSRF/CORS próprios — a autenticação é JWT do backend; o token vive na sessão Streamlit (memória do processo).

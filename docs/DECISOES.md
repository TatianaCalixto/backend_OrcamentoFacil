# Decisões técnicas — OrçaFácil

Histórico de decisões não-óbvias tomadas durante a execução. Espelha a aba "Decisões" da planilha operacional.

## DEC-001 — Split em dois repositórios GitHub (Sprint 0)

**Contexto:** O blueprint original previa monorepo único com `backend/`, `mobile/`, `panel/`, `docs/`, `scripts/`. A usuária forneceu dois repos GitHub prontos: `backend_OrcamentoFacil` e `frontend_OrcamentoFacil`.

**Decisão:** Split por papel —
- `backend_OrcamentoFacil`: `backend/`, `panel/`, `docs/`, `scripts/` (Python + docs)
- `frontend_OrcamentoFacil`: `mobile/` (Flutter)

**Alternativas consideradas:**
- A) Forçar monorepo em um dos dois repos.
- B) Split natural por papel **(escolhida)**.
- C) Git submodules.
- D) Pedir um terceiro repo só para o painel.

**Justificativa:** Painel Streamlit fica com backend por compartilhar stack Python e por consumir o mesmo banco/contexto. Mobile fica isolado por ter ciclo de release próprio (APK). docs/ e scripts/ ficam no backend repo (devops/python-centric).

**Impacto:** Planilha de planejamento permanece no workspace root (fora dos dois repos de código), pois é artefato operacional do ciclo de planejamento.

---

## DEC-002 (implícita) — pin `bcrypt>=4.0,<4.1` (Sprint 2)

**Contexto:** `passlib` 1.7.4 (último release oficial) faz `bcrypt.__about__.__version__`, atributo removido em `bcrypt` >= 4.1.

**Decisão:** Pin `bcrypt>=4.0,<4.1` em `requirements.txt`.

**Alternativas:** trocar passlib por bcrypt direto, ou por argon2.

**Justificativa:** Spec do projeto pede `passlib[bcrypt]` explicitamente. Pin é workaround temporário até passlib ser atualizado ou trocarmos a lib em futura sprint.

---

## DEC-003 (implícita) — Status de Budget calculado em runtime, não persistido (Sprint 6)

**Contexto:** Budget tem campo derivado `status` (ok/warning/critical) baseado em `percent_used`.

**Decisão:** Não persistir status no banco. Calcular no GET.

**Alternativas:** materializar via trigger ou cache.

**Justificativa:** Status muda toda vez que uma transação é criada/editada/deletada. Materializar exigiria recalcular em N pontos. Calcular em runtime é simples e barato; índices em (user_id, category_id, date) tornam a soma O(log n).

---

## DEC-004 (implícita) — 404 em vez de 403 para isolamento entre usuários (Sprint 3+)

**Contexto:** Quando usuário B tenta acessar conta de usuário A, qual status?

**Decisão:** Retornar **404 "não encontrado"** (não 403 "proibido").

**Justificativa:** 403 vazaria a existência do recurso. 404 trata como se ele não existisse para o usuário corrente.

---

## DEC-005 (implícita) — Cobertura gate em pytest.ini (Sprint 10)

**Contexto:** Spec pedia "cobertura ≥ 80%".

**Decisão:** Configurar `--cov-fail-under=80` em `pytest.ini` (addopts), fazendo o CI quebrar se cair abaixo.

**Alternativas:** validar manualmente, ou via job separado no CI.

**Justificativa:** Gate no pytest.ini é local + CI ao mesmo tempo, sem duplicação. Cobertura atual: 96.6%.

---

## DEC-006 (implícita) — Streamlit panel separado por pages/ (Sprint 15)

**Contexto:** Streamlit suporta múltiplas páginas via pasta `pages/`.

**Decisão:** Login em `app.py` (raiz) + páginas separadas em `pages/1_Relatorios.py` e `pages/2_Transacoes.py`.

**Justificativa:** Padrão idiomático do Streamlit. Numeração no nome do arquivo controla a ordem do menu lateral.

---

## DEC-007 (implícita) — Sinal do valor no CSV define o tipo (Sprint 9)

**Contexto:** CSVs de extrato bancário brasileiro usam sinal negativo para débitos.

**Decisão:** No parser de import CSV:
- `amount > 0` → income
- `amount < 0` → expense (armazena valor absoluto)
- `amount == 0` → erro

**Alternativas:** coluna separada para tipo, ou regex sobre descrição.

**Justificativa:** Casa com o padrão dos bancos brasileiros (CEF, Itaú, Nubank). Outras convenções podem ser suportadas via parser dedicado no futuro.

---

## DEC-008 (implícita) — Dois agentes paralelos para acelerar backend + frontend (sessão única)

**Contexto:** Backend e frontend são desacoplados após contratos da API estarem estáveis.

**Decisão:** Spawnar agente Claude em background para frontend (Sprints 11, 12, 13, 14) enquanto o agente principal continua com backend (Sprints 5-10, 15, 16).

**Alternativas:** rodar sequencial, ou múltiplos agentes intercalados.

**Justificativa:** Frontend só depende da API; após auth (Sprint 2) e dashboard (Sprint 8), o frontend pode evoluir independente. Coordenação via planilha (linhas distintas por sprint, releitura imediata antes de cada save).

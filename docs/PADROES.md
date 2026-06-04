# Padrões de código — Backend OrçaFácil

Convenções transversais do backend. Criado na S24-T05 (Fase 4). Complementa
[`ARQUITETURA.md`](ARQUITETURA.md) e [`DECISOES.md`](DECISOES.md).

---

## 1. Formato padronizado de erro

Toda resposta de erro da API usa **um único envelope JSON**, montado pelos
exception handlers em [`app/core/errors.py`](../backend/app/core/errors.py):

```json
{
  "detail": "<mensagem ou estrutura>",
  "code": "<código estável>",
  "request_id": "<uuid de correlação>"
}
```

| Campo        | Descrição                                                                                  |
| ------------ | ------------------------------------------------------------------------------------------ |
| `detail`     | Mensagem legível em PT-BR (string) ou, na validação 422, a lista de erros do Pydantic.      |
| `code`       | Código estável para o cliente programar em cima (não muda com o texto da mensagem).        |
| `request_id` | UUID de correlação; também devolvido no header `X-Request-ID` para rastrear no log.         |

### Códigos (`code`) por tipo de falha

| Situação                              | HTTP | `code`             |
| ------------------------------------- | ---- | ------------------ |
| Erro de regra/permissão/recurso       | 4xx  | `http_<status>` (ex.: `http_404`) |
| Validação de payload (Pydantic)       | 422  | `validation_error` |
| Exceção não tratada                   | 500  | `internal_error`   |

### Convenção de status HTTP

| Status | Quando usar                                                                 |
| ------ | --------------------------------------------------------------------------- |
| 400    | Requisição malformada que não é validação de schema (ex.: arquivo inválido).|
| 401    | Não autenticado / credenciais inválidas / token inválido.                   |
| 404    | Recurso não encontrado **ou** não pertence ao usuário (não vaza existência).|
| 409    | Conflito (ex.: e-mail já cadastrado).                                        |
| 422    | Falha de validação de schema (gerada pelo FastAPI/Pydantic).                |
| 429    | Rate limit estourado (inclui header `Retry-After`).                         |
| 500    | Erro interno; o `detail` é genérico ("erro interno do servidor").           |

> **404 em vez de 403** para recursos de outro usuário: a API responde "não
> encontrado" para não revelar a existência de IDs alheios.

### Exemplos

```jsonc
// 401
{ "detail": "não autenticado", "code": "http_401", "request_id": "…" }

// 404
{ "detail": "transação não encontrada", "code": "http_404", "request_id": "…" }

// 409
{ "detail": "email já cadastrado", "code": "http_409", "request_id": "…" }

// 422 (detail = lista do Pydantic)
{ "detail": [ { "type": "...", "loc": ["body","amount"], "msg": "..." } ],
  "code": "validation_error", "request_id": "…" }
```

---

## 2. Convenção de mensagens (`detail`)

1. **Idioma único: PT-BR, sempre com acentuação correta.** Nada de mensagens
   mistas pt/en. Ex.: `categoria não pertence ao usuário` (não
   `category nao pertence ao usuario`).
2. **Minúsculas no início**, sem ponto final. Curtas e objetivas. Ex.:
   `conta não encontrada`, `valor zero não é permitido`.
3. **Termos técnicos consagrados** permanecem como estão (são *loanwords*, não
   "mensagem em inglês"): `token`, `refresh token`, `JWT`, `CSV`, `bytes`,
   `pix`, `e-mail`/`email`. A regra mira palavras com tradução natural óbvia
   (account→conta, category→categoria, budget→orçamento, color→cor,
   header→cabeçalho).
4. **Não vazar interno**: nada de stack trace, SQL, nome de tabela ou caminho
   de arquivo no `detail`. O 500 usa sempre o texto genérico
   `erro interno do servidor`; a causa real vai só para o log (com
   `request_id`).
5. **`code` é o contrato estável**, não o texto. Clientes devem ramificar por
   `code`/status, não por `detail` (que pode ser ajustado/localizado).

### Catálogo de mensagens canônicas

| Domínio       | HTTP | `detail`                                                |
| ------------- | ---- | ------------------------------------------------------- |
| auth          | 401  | `não autenticado`                                       |
| auth          | 401  | `credenciais inválidas`                                 |
| auth          | 401  | `refresh token inválido`                                |
| auth          | 401  | `refresh token não pertence ao usuário autenticado`     |
| auth          | 409  | `email já cadastrado`                                   |
| users (422)   | 422  | `email inválido` / `senha deve ter no mínimo 8 caracteres` / `senha deve conter ao menos 1 letra` / `senha deve conter ao menos 1 número` |
| accounts      | 404  | `conta não encontrada`                                  |
| categories    | 404  | `categoria não encontrada`                              |
| categories(422)| 422 | `cor deve estar no formato #rrggbb` / `cor deve ser um hexadecimal válido` |
| transactions  | 404  | `transação não encontrada`                              |
| transactions  | 404  | `conta não encontrada ou não pertence ao usuário`       |
| transactions  | 404  | `categoria não encontrada ou não pertence ao usuário`   |
| budgets       | 404  | `orçamento não encontrado`                              |
| budgets       | 404  | `categoria não pertence ao usuário`                     |
| goals         | 404  | `meta não encontrada`                                   |
| imports       | 400  | `arquivo precisa ter extensão .csv` / `tipo de conteúdo não suportado: …` / `arquivo vazio` / `arquivo excede N bytes` |
| imports       | 404  | `conta não pertence ao usuário`                         |
| imports (CSV) | —    | `CSV vazio` / `cabeçalho inválido: colunas exigidas data, descrição, valor` / `data inválida: …` / `valor inválido: …` / `valor zero não é permitido` / `descrição vazia` |

> Erros de parsing do CSV (última linha da tabela) não derrubam o import: cada
> linha problemática vira um item em `errors[]` no `ImportResult`, com
> `line_number` e `message`.

---

## 3. Onde os handlers vivem

- `RequestIdMiddleware` gera/propaga o `request_id` e o header `X-Request-ID`.
- `http_exception_handler` → envelope para qualquer `HTTPException`.
- `validation_exception_handler` → 422 com a lista do Pydantic em `detail`.
- `unhandled_exception_handler` → 500 genérico, logando a exceção real.

Registrados via `register_error_handlers(app)` em `app/main.py`.

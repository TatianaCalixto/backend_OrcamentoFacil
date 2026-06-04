"""Parser de CSV de extratos bancarios + regras de categorizacao (S09-T02).

Formato suportado:
- Delimitador: virgula ou ponto-e-virgula (auto-detectado).
- Header obrigatorio. Aceita variacoes pt/en: data|date, descricao|descrição|
  description, valor|amount.
- Datas: ISO (YYYY-MM-DD) ou BR (DD/MM/YYYY ou DD-MM-YYYY).
- Valor: aceita "R$ 1.234,56" (BR), "1,234.56" (US), "-1234.56", "1234.56".
- Sinal define o tipo: amount > 0 = receita; amount < 0 = despesa (padrao
  de extratos brasileiros).

Categorizacao automatica por palavra-chave (case-insensitive) na descricao,
mapeada para o NOME da categoria do usuario. Fallback: "Outros".
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.transactions.models import TransactionType

# ----- mapa de regras (substring na descricao -> nome de categoria) -----
CATEGORIZATION_RULES: list[tuple[str, str]] = [
    ("UBER", "Transporte"),
    ("99 ", "Transporte"),
    ("IFOOD", "Alimentacao"),
    ("RAPPI", "Alimentacao"),
    ("NETFLIX", "Assinaturas"),
    ("SPOTIFY", "Assinaturas"),
    ("AMAZON PRIME", "Assinaturas"),
    ("DROGARIA", "Saude"),
    ("FARMACIA", "Saude"),
]
FALLBACK_CATEGORY_NAME = "Outros"


@dataclass
class ParsedLine:
    line_number: int  # 1-based, inclui header
    date: date_type
    description: str
    amount: Decimal  # SEMPRE positivo
    type: TransactionType
    suggested_category_name: str


@dataclass
class ParseError:
    line_number: int
    message: str


@dataclass
class ParseResult:
    rows: list[ParsedLine]
    errors: list[ParseError]


# ----- helpers -----


def _normalize_header(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.strip().lower()


_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")


def _parse_date(raw: str) -> date_type:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"data inválida: {raw!r}")


_MONEY_RE = re.compile(r"^-?(R\$\s*)?([\d.,]+)$")


def _parse_amount(raw: str) -> Decimal:
    raw = raw.strip().replace(" ", "")
    if not raw:
        raise ValueError("valor vazio")
    m = _MONEY_RE.match(raw)
    if not m:
        raise ValueError(f"valor inválido: {raw!r}")
    sign = "-" if raw.startswith("-") else ""
    n = m.group(2)
    # decidir separador decimal: o ULTIMO de '.' ou ',' eh o decimal
    last_dot = n.rfind(".")
    last_comma = n.rfind(",")
    if last_dot == -1 and last_comma == -1:
        s = n
    elif last_comma > last_dot:
        # virgula eh decimal (BR): remove pontos (milhar), troca virgula
        s = n.replace(".", "").replace(",", ".")
    else:
        # ponto eh decimal (US): remove virgulas (milhar)
        s = n.replace(",", "")
    try:
        return Decimal(sign + s)
    except InvalidOperation as e:
        raise ValueError(f"valor inválido: {raw!r}") from e


def _categorize(description: str) -> str:
    upper = description.upper()
    for keyword, category in CATEGORIZATION_RULES:
        if keyword in upper:
            return category
    return FALLBACK_CATEGORY_NAME


def _find_column(header_map: dict[str, int], *candidates: str) -> int | None:
    for c in candidates:
        if c in header_map:
            return header_map[c]
    return None


# ----- parser principal -----


def parse_csv(content: bytes) -> ParseResult:
    text = content.decode("utf-8-sig", errors="replace")
    # detectar delimitador (tenta sniff, fallback ;)
    sample = text[:1024]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error:
        # fallback: vira separador mais comum nas primeiras linhas
        delim = ";" if sample.count(";") > sample.count(",") else ","

        class _D(csv.excel):
            delimiter = delim

        dialect = _D

    reader = csv.reader(io.StringIO(text), dialect=dialect)
    try:
        header = next(reader)
    except StopIteration:
        return ParseResult(rows=[], errors=[ParseError(line_number=1, message="CSV vazio")])

    header_map = {_normalize_header(c): i for i, c in enumerate(header)}
    date_col = _find_column(header_map, "data", "date")
    desc_col = _find_column(header_map, "descricao", "description", "historico")
    amount_col = _find_column(header_map, "valor", "amount", "value")

    if date_col is None or desc_col is None or amount_col is None:
        return ParseResult(
            rows=[],
            errors=[
                ParseError(
                    line_number=1,
                    message="cabeçalho inválido: colunas exigidas data, descrição, valor",
                )
            ],
        )

    rows: list[ParsedLine] = []
    errors: list[ParseError] = []
    for i, raw_row in enumerate(reader, start=2):
        if not raw_row or all(not c.strip() for c in raw_row):
            continue
        try:
            dt = _parse_date(raw_row[date_col])
            desc = raw_row[desc_col].strip()
            if not desc:
                raise ValueError("descrição vazia")
            amount = _parse_amount(raw_row[amount_col])
            if amount == 0:
                raise ValueError("valor zero não é permitido")
            t = TransactionType.EXPENSE if amount < 0 else TransactionType.INCOME
            rows.append(
                ParsedLine(
                    line_number=i,
                    date=dt,
                    description=desc,
                    amount=abs(amount),
                    type=t,
                    suggested_category_name=_categorize(desc),
                )
            )
        except (IndexError, ValueError) as e:
            errors.append(ParseError(line_number=i, message=str(e)))

    return ParseResult(rows=rows, errors=errors)

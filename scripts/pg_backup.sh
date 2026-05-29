#!/usr/bin/env bash
# Backup automatizado do Postgres do OrçaFácil (S22-T05).
#
# Gera um dump comprimido (formato custom do pg_dump) com timestamp UTC e aplica
# retenção simples por dias. Pensado para rodar em cron / job agendado. O restore
# manual está documentado em docs/DEPLOY.md.
#
# Uso:
#   DATABASE_URL=postgresql://user:pass@host:5432/db ./scripts/pg_backup.sh
#
# Variáveis:
#   DATABASE_URL    (obrigatória) string de conexão Postgres.
#   BACKUP_DIR      (opcional) diretório de saída. Default: ./backups
#   RETENTION_DAYS  (opcional) dias de retenção. Default: 7
#
# Requer: pg_dump no PATH (pacote postgresql-client).
set -euo pipefail

: "${DATABASE_URL:?defina DATABASE_URL (postgresql://...)}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# O app usa o driver "+psycopg" na URL; o pg_dump espera postgresql:// puro.
PG_URL="${DATABASE_URL/+psycopg/}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/orcafacil_${STAMP}.dump"

echo "[pg_backup] iniciando dump -> $OUT"
pg_dump --format=custom --no-owner --no-privileges --dbname="$PG_URL" --file="$OUT"
echo "[pg_backup] concluído ($(du -h "$OUT" | cut -f1))"

# Retenção: remove dumps mais antigos que RETENTION_DAYS.
find "$BACKUP_DIR" -name 'orcafacil_*.dump' -type f -mtime +"${RETENTION_DAYS}" -delete 2>/dev/null || true
echo "[pg_backup] retenção aplicada (mantém últimos ${RETENTION_DAYS} dias)"

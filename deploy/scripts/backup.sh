#!/usr/bin/env sh
set -eu

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$OUT_DIR"

docker compose -f docker-compose.yml exec -T db \
  pg_dump -U "${POSTGRES_USER:-ijiedong}" -d "${POSTGRES_DB:-ijiedong}" \
  | gzip > "$OUT_DIR/ijiedong-$STAMP.sql.gz"

find "$OUT_DIR" -type f -name 'ijiedong-*.sql.gz' -mtime +7 -delete
echo "backup written: $OUT_DIR/ijiedong-$STAMP.sql.gz"

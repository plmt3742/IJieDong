#!/usr/bin/env sh
set -eu

if [ "${1:-}" = "" ]; then
  echo "usage: $0 <backup.sql.gz>" >&2
  exit 2
fi

gzip -dc "$1" | docker compose -f docker-compose.yml exec -T db \
  psql -U "${POSTGRES_USER:-ijiedong}" -d "${POSTGRES_DB:-ijiedong}"
echo "restore finished from $1"

#!/bin/sh
set -e

# Wait for Postgres (db:5432 by default) before creating tables.
# DATABASE_URL looks like postgresql+asyncpg://user:pass@host:port/db
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

echo "Waiting for Postgres at ${DB_HOST}:${DB_PORT}..."
for i in $(seq 1 30); do
  if python -c "import socket,sys; s=socket.create_connection(('${DB_HOST}', ${DB_PORT}), timeout=2); s.close()" 2>/dev/null; then
    echo "Postgres is up."
    break
  fi
  if [ "$i" = "30" ]; then
    echo "Postgres not reachable after 30s, continuing anyway..." >&2
    break
  fi
  sleep 1
done

python init_db.py

exec uvicorn app.main:app --host 0.0.0.0 --port 8000

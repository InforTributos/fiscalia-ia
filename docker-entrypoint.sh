#!/bin/bash
set -e

# ──────────────────────────────────────────────
# wait-for-postgres: espera a que PostgreSQL esté listo
# Solo aplica cuando POSTGRES_HOST no es localhost
# ──────────────────────────────────────────────
if [ -n "$POSTGRES_HOST" ] && [ "$POSTGRES_HOST" != "localhost" ]; then
  echo "→ Esperando PostgreSQL en ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."

  for i in $(seq 1 30); do
    if python3 -c "
import asyncio, os, sys

async def check():
    import asyncpg
    try:
        conn = await asyncpg.connect(
            host=os.environ.get('POSTGRES_HOST', 'localhost'),
            port=int(os.environ.get('POSTGRES_PORT', 5432)),
            user=os.environ.get('POSTGRES_USER', 'fiscalia'),
            password=os.environ.get('POSTGRES_PASSWORD', ''),
            database=os.environ.get('POSTGRES_DB', 'fiscalia'),
            timeout=2,
        )
        await conn.close()
        return True
    except Exception:
        return False

sys.exit(0 if asyncio.run(check()) else 1)
" 2>/dev/null; then
      echo "✓ PostgreSQL listo (intento $i)"
      break
    fi

    if [ "$i" -eq 30 ]; then
      echo "✗ PostgreSQL no respondió tras 30 intentos — abortando"
      exit 1
    fi

    sleep 1
  done
fi

exec "$@"

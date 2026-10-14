#!/usr/bin/env bash
# Copia la base de producción (Render) a la base local ligas_europeas.
#
# Solo LEE de producción (pg_dump). La base local se reemplaza únicamente si la
# copia completa se cargó sin errores: se construye en una base temporal y al
# final se intercambian los nombres, así un fallo a medias nunca deja la local
# vacía o corrupta.
#
# Uso manual:   ./scripts/sync-local-from-prod.sh
# Automático:   ./scripts/install-sync-mac.sh   (tarea programada de macOS)
#
# Variables opcionales:
#   PROD_ENV_FILE  archivo con DATABASE_URL de producción (def.: <repo>/.env.production)
#   LOCAL_DB       nombre de la base local (def.: ligas_europeas)
set -euo pipefail

# launchd arranca con un PATH mínimo; Homebrew (Apple Silicon) en /opt/homebrew.
# Producción corre Postgres 18 y pg_dump debe ser de versión >= a la del
# servidor, por eso se usa el 18 para el dump y la carga; el servidor local
# (16) se maneja con sus propios binarios.
PG18=/opt/homebrew/opt/postgresql@18/bin
PG16=/opt/homebrew/opt/postgresql@16/bin
export PATH="$PG16:$PG18:/opt/homebrew/bin:/usr/bin:/bin"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROD_ENV_FILE="${PROD_ENV_FILE:-$REPO_DIR/.env.production}"
LOCAL_DB="${LOCAL_DB:-ligas_europeas}"
NEW_DB="${LOCAL_DB}_sync_new"
OLD_DB="${LOCAL_DB}_sync_old"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
die() { log "ERROR: $*"; exit 1; }

[ -f "$PROD_ENV_FILE" ] || die "No existe $PROD_ENV_FILE (pídelo al mantenedor; no se versiona)."
[ -x "$PG18/pg_dump" ] || die "Falta postgresql@18 (brew install postgresql@18)."
[ -x "$PG16/psql" ]    || die "Falta postgresql@16 (brew install postgresql@16)."

# Se lee solo DATABASE_URL, sin 'source' del archivo completo.
DATABASE_URL="$(grep -E '^DATABASE_URL=' "$PROD_ENV_FILE" | head -1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//')"
[ -n "$DATABASE_URL" ] || die "$PROD_ENV_FILE no tiene DATABASE_URL."

pg_isready -q -h localhost || die "Postgres local no responde (brew services start postgresql@16)."

# Evita dos sincronizaciones a la vez (p. ej. manual + programada).
LOCK_DIR="${TMPDIR:-/tmp}/55sportsbet-sync.lock"
mkdir "$LOCK_DIR" 2>/dev/null || die "Ya hay otra sincronización en curso ($LOCK_DIR)."
WORK_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$WORK_DIR"; rmdir "$LOCK_DIR" 2>/dev/null || true
  # Si algo falló antes del intercambio, no dejar la base temporal.
  dropdb -h localhost --if-exists "$NEW_DB" >/dev/null 2>&1 || true
}
trap cleanup EXIT

log "Descargando producción (solo lectura)..."
"$PG18/pg_dump" "$DATABASE_URL" --no-owner --no-privileges -f "$WORK_DIR/dump.sql" \
  || die "pg_dump falló; la base local no se tocó."
grep -q '^CREATE TABLE' "$WORK_DIR/dump.sql" || die "El dump no contiene tablas; la base local no se tocó."

# 'transaction_timeout' es un parámetro de Postgres 17+; el servidor local (16)
# lo rechazaría y con ON_ERROR_STOP abortaría una copia que está bien.
sed -i '' '/^SET transaction_timeout/d' "$WORK_DIR/dump.sql"

log "Cargando en base temporal $NEW_DB..."
dropdb -h localhost --if-exists "$NEW_DB"
createdb -h localhost "$NEW_DB"
"$PG18/psql" -h localhost -q -v ON_ERROR_STOP=1 -d "$NEW_DB" -f "$WORK_DIR/dump.sql" >/dev/null \
  || die "La carga falló; la base local no se tocó."

MATCHES="$(psql -h localhost -Atc 'SELECT count(*) FROM matches' "$NEW_DB")"
[ "${MATCHES:-0}" -gt 0 ] || die "La copia quedó sin partidos; la base local no se tocó."

log "Intercambiando $NEW_DB -> $LOCAL_DB (cierra conexiones abiertas, p. ej. uvicorn)..."
for db in "$LOCAL_DB" "$NEW_DB"; do
  psql -h localhost -qAt -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$db' AND pid <> pg_backend_pid()" >/dev/null
done
dropdb -h localhost --if-exists "$OLD_DB"
if psql -h localhost -Atc "SELECT 1 FROM pg_database WHERE datname='$LOCAL_DB'" postgres | grep -q 1; then
  psql -h localhost -q -d postgres -c "ALTER DATABASE \"$LOCAL_DB\" RENAME TO \"$OLD_DB\""
fi
psql -h localhost -q -d postgres -c "ALTER DATABASE \"$NEW_DB\" RENAME TO \"$LOCAL_DB\""
dropdb -h localhost --if-exists "$OLD_DB"

LAST="$(psql -h localhost -Atc 'SELECT max(date) FROM matches' "$LOCAL_DB")"
log "Listo: $LOCAL_DB actualizada ($MATCHES partidos, último en $LAST)."

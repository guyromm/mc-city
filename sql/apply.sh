#!/bin/bash
# Replay this project's schema (sql/schema = pg_schema_dump.py output, the SOURCE OF TRUTH), then seed data, then the JWT
# secret row (if the project keeps it as data in <project>.secrets), then claude-ui's own schema.
# Runs as the owner role (local peer auth). Works on the live DB and on an empty one: existing tables/constraints are
# reported and skipped; views/functions are CREATE OR REPLACE; grants are idempotent. Any OTHER error exits 1.
#   sql/apply.sh            replay into $DB_NAME (live)
#   sql/apply.sh --fresh    drop + recreate every object in ${DB_NAME}_test (owned by you) and replay there:
#                           proves an EMPTY database rebuilds. Then: python3 pg_schema_dump.py --db ${DB_NAME}_test
#                           into a scratch checkout, or compare `pg_dump -s` of both DBs.
#   --no-seed               skip sql/seed/*.sql
# Workflow for a schema change: change the DB (psql, or write sql/migrations/<date>-<what>.sql and psql -f it),
# run `python3 pg_schema_dump.py`, review `git diff sql/schema`, commit both. Never leave a live change undumped.
# (skeleton from resource-manager tools/project/skeleton; house convention doc:pg-schema-dump-fb-collect, thread #978)
set -e
cd "$(dirname "$0")"; set -a; source ../.env; set +a
PROJECT="${DB_NAME:-$(id -un)}"
DB="$PROJECT"; SEED=1
for a in "$@"; do case "$a" in
  --fresh) DB="${PROJECT}_test" ;;
  --no-seed) SEED= ;;
  *) echo "usage: $0 [--fresh] [--no-seed]"; exit 2 ;;
esac; done
export PGOPTIONS="-c client_min_messages=warning"
if [ "$DB" != "$PROJECT" ]; then   # wipe the scratch DB (only ever *_test) back to empty
  # not DROP OWNED: it also revokes the role's privileges on shared objects (its live DB's ACL)
  psql -d "$DB" -v ON_ERROR_STOP=1 -q <<'SQL'
DO $$ DECLARE s text; BEGIN
  FOR s IN SELECT nspname FROM pg_namespace WHERE nspowner = current_user::regrole AND nspname <> 'public' LOOP
    EXECUTE format('DROP SCHEMA %I CASCADE', s); END LOOP;
  FOR s IN SELECT extname FROM pg_extension WHERE extowner = current_user::regrole LOOP
    EXECUTE format('DROP EXTENSION %I CASCADE', s); END LOOP;
END $$;
SQL
fi
EXPECTED='already exists|multiple primary keys|must be owner of extension|permission denied to create extension'
errs=$( (cat schema/00; while read -r f; do [ -n "$f" ] && cat "schema/$f"; done < schema/order.txt) \
        | psql -d "$DB" -v ON_ERROR_STOP=0 -q 2>&1 | grep -i 'error' | grep -viE "$EXPECTED" || true)
if [ -n "$SEED" ]; then for f in seed/*.sql; do [ -e "$f" ] && psql -d "$DB" -v ON_ERROR_STOP=1 -q -f "$f"; done; fi
# the JWT secret PostgREST verifies is data (<project>.secrets), synced from .env, never in a file
S="${PGRST_JWT_SECRET:-$JWT_SECRET}"
if [ -n "$S" ] && [ "$(psql -d "$DB" -Atc "select to_regclass('$PROJECT.secrets') is not null")" = t ]; then
  psql -d "$DB" -v ON_ERROR_STOP=1 -q -v s="$S" -v t="$PROJECT.secrets" <<'SQL'
INSERT INTO :t(k,v) VALUES ('jwt_secret', :'s') ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v;
SQL
fi
if [ -x ../claude-ui/sql/apply.sh ]; then
  DBURI="dbname=$DB" CLAUDE_UI_SCHEMA="${CLAUDE_UI_SCHEMA:-$PROJECT}" CLAUDE_UI_ADMIN_FN="${CLAUDE_UI_ADMIN_FN:-$PROJECT.is_admin()}" \
    CLAUDE_UI_ANON_ROLE="${PROJECT}_anon" CLAUDE_UI_AUTH_ROLE="${PROJECT}_web" ../claude-ui/sql/apply.sh >/dev/null
  # board #5130: CHECK OPTION on claude-ui's api views (until our claude-ui pin carries upstream review 527)
  psql -d "$DB" -v ON_ERROR_STOP=1 -q -f migrations/2026-11-28-claude-views-check-option.sql
fi
psql -d "$DB" -qc "NOTIFY pgrst, 'reload schema';"
[ -n "$errs" ] && { echo "UNEXPECTED ERRORS ($DB):"; echo "$errs"; exit 1; }
echo "applied to $DB"

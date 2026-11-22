#!/bin/bash
# minecraft backups (#288, from auth's backup.sh). Daily from cron:
#   1. pg_dump -Fc of DB minecraft (whole DB) -> ~/backups/minecraft-<UTC stamp>.dump (keep KEEP_DAYS locally)
#   1b. the BDS world (consistent live copy, scripts/world-backup.sh) + server.properties/allowlist/permissions
#      -> ~/backups/world-<UTC stamp>.tgz (keep KEEP_DAYS); skipped with a warning while no BDS is installed
#   1c. encrypted secrets bundle (age, the recovery key, #276/1) -> ~/backups/secrets-<stamp>.tar.gz.age
#   2. offsite: rsync to minecraft's OWN Storage Box sub-account (port 23, key ~/.ssh/id_ed25519) when
#      BACKUP_SB_USER / BACKUP_SB_HOST are in .env; skipped with a warning until guy creates it
#   3. restore test: pg_restore into $RESTORE_DB (default minecraft_test, the scratch DB, emptied first)
#      and compare per-table row counts with the source
# Exit non-zero on any failure, and tell the Claude pane. Status line appended to logs/backup.status.
#   bash backup.sh [--no-offsite] [--no-restore]
set -uo pipefail
umask 077
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"; cd "$DIR"
set -a; source .env; set +a
BK="$DIR/backups"; mkdir -p "$BK" "$DIR/logs"; chmod 700 "$BK"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"; RESTORE_DB="${RESTORE_DB:-minecraft_test}"
stamp=$(date -u +%Y%m%d-%H%M); f="$BK/minecraft-$stamp.dump"; status=ok; notes=()
fail() { status=FAIL; notes+=("$*"); echo "FAIL: $*" >&2; }

# per-table row counts over every user schema the owner can see
counts_sql="select coalesce(string_agg(format('%s.%s=%s', s, t, (xpath('/row/c/text()', query_to_xml(format('select count(*) c from %I.%I', s, t), false, true, '')))[1]::text), ' ' order by s, t), '') from (select schemaname s, tablename t from pg_tables where schemaname not in ('pg_catalog','information_schema')) x"
src_counts=$(psql "$DBURI" -Atc "$counts_sql") || fail "count source"
if pg_dump -Fc --no-owner "$DBURI" -f "$f.part" && mv "$f.part" "$f"; then
  chmod 600 "$f"; sha256sum "$f" | awk '{print $1}' > "$f.sha256"; echo "$src_counts" > "$f.counts"
  notes+=("dump $(basename "$f") $(du -h "$f" | cut -f1)")
else rm -f "$f.part"; fail "pg_dump"; fi
find "$BK" -name 'minecraft-*.dump*' -mtime +"$KEEP_DAYS" -delete

# 1b. world
if [ -d "${MC_BDS:-$HOME/mc-bds}/server/worlds/claude_build" ]; then
  w="$BK/world-$stamp.tgz"
  if r=$(bash "$DIR/scripts/world-backup.sh" "$w" 2>&1 | tail -1) && [ -s "$w" ]; then
    chmod 600 "$w"; sha256sum "$w" | awk '{print $1}' > "$w.sha256"; notes+=("world $(basename "$w") ($r)")
  else fail "world backup: $r"; fi
else notes+=("world SKIPPED (no BDS world yet)"); status=${status/ok/warn}; fi
find "$BK" -name 'world-*.tgz*' -mtime +"$KEEP_DAYS" -delete

# 1c. secrets bundle (#276/1, doc:infra-map): .env, SSH key, board token, Xbox login token -> encrypted straight to the ONE
#     recovery key (guy holds the private key; this host can write the bundle but never read it back). tar | age: no
#     plaintext ever touches the disk. Extra recipients: BACKUP_AGE_EXTRA (space-separated age1... keys) in .env.
RECOVERY_KEY=age1rgv7klzpwpr8tfxt0ejza5rk6uhwhmg5q2y85eclz7kfscejlqaspg8xqu
AGE=$(command -v age || echo "$HOME/.local/bin/age")
sf=(.env .ssh/id_ed25519 .ssh/id_ed25519.pub .ssh/known_hosts .board/token .board/config mcxb/config.yml mcxb/cache/cache.json)
have=(); for p in "${sf[@]}"; do [ -e "$HOME/$p" ] && have+=("$p"); done
s="$BK/secrets-$stamp.tar.gz.age"; rcp=(-r "$RECOVERY_KEY"); for k in ${BACKUP_AGE_EXTRA:-}; do rcp+=(-r "$k"); done
if [ -x "$AGE" ] && tar czf - -C "$HOME" "${have[@]}" | "$AGE" "${rcp[@]}" -o "$s.part" && mv "$s.part" "$s"; then
  chmod 600 "$s"; sha256sum "$s" | awk '{print $1}' > "$s.sha256"; notes+=("secrets $(basename "$s") (${#have[@]} files, age)")
else rm -f "$s.part"; fail "secrets bundle (age at $AGE)"; fi
find "$BK" -name 'secrets-*.tar.gz.age*' -mtime +"$KEEP_DAYS" -delete

# 2. offsite
if [[ " $* " != *" --no-offsite "* ]]; then
  if [ -n "${BACKUP_SB_USER:-}" ] && [ -n "${BACKUP_SB_HOST:-}" ] && [ -f "$f" ]; then
    if rsync -a --delete -e "ssh -p 23 -i $HOME/.ssh/id_ed25519 -o BatchMode=yes" \
         "$BK/" "$BACKUP_SB_USER@$BACKUP_SB_HOST:minecraft/"; then notes+=("offsite ok")
    else fail "offsite rsync"; fi
  else notes+=("offsite SKIPPED (no BACKUP_SB_* in .env yet)"); status=${status/ok/warn}; fi
fi

# 3. restore test (wipes RESTORE_DB: only schemas/extensions owned by this role, as sql/apply.sh --fresh)
if [[ " $* " != *" --no-restore "* ]] && [ -f "$f" ]; then
  RURI=$(sed -E "s#^(.*://[^/]*/)[^?]*#\1$RESTORE_DB#" <<<"$DBURI")
  if psql "$RURI" -Atc "select 1" >/dev/null 2>&1; then
    psql "$RURI" -q -v ON_ERROR_STOP=1 <<'SQL' && pg_restore --no-owner --no-privileges -d "$RURI" "$f" 2>"$BK/restore.err" || true
set client_min_messages=warning;
DO $$ DECLARE s text; BEGIN
  FOR s IN SELECT nspname FROM pg_namespace WHERE nspowner = current_user::regrole AND nspname <> 'public' LOOP
    EXECUTE format('DROP SCHEMA %I CASCADE', s); END LOOP;
  FOR s IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner = current_user LOOP
    EXECUTE format('DROP TABLE public.%I CASCADE', s); END LOOP;
END $$;
SQL
    # superuser-installed extensions already exist in the scratch DB: those errors are expected
    grep -iE "error" "$BK/restore.err" | grep -viE "already exists|must be owner of extension|permission denied to create extension|errors ignored on restore" >/dev/null \
      && fail "pg_restore (see backups/restore.err)"
    got=$(psql "$RURI" -Atc "$counts_sql")
    [ "$got" = "$src_counts" ] && notes+=("restore test ok ($got)") || fail "restore counts differ: src[$src_counts] restored[$got]"
  else notes+=("restore test SKIPPED (no DB $RESTORE_DB)"); status=${status/ok/warn}; fi
fi

line="$(date -u +%FT%TZ) $status: ${notes[*]}"; echo "$line" | tee -a "$DIR/logs/backup.status"
# ~/.backup-status (resource-manager's staleness check reads the newest "ok" line): <status> <time> <where> <bytes>
where=$([[ " ${notes[*]} " == *"offsite ok"* ]] && echo "offsite:minecraft/$(basename "$f")" || echo "local:backups/$(basename "$f")")
echo "$status $(date -u +%FT%TZ) $where $(stat -c %s "$f" 2>/dev/null || echo 0)" >> "$HOME/.backup-status"; chmod 644 "$HOME/.backup-status"
if [ "$status" = FAIL ]; then
  source "$DIR/tmux.sh" >/dev/null 2>&1 && notify_claude "backup.sh FAILED: ${notes[*]}"; exit 1; fi

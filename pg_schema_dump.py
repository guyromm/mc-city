#!/usr/bin/env python3
"""Dump this project's PostgreSQL schema into sql/schema/, one file per object: the schema's SOURCE OF TRUTH.
House convention (doc:pg-schema-dump-fb-collect, contract board thread #978). Generic skeleton copy shipped by
resource-manager (tools/project/skeleton), from crosspost's adaptation (11-12).

- connects as the project's owner role by local peer auth (`pg_dump -d $DB_NAME`); DBURI in .env is the PostgREST
  login role, which cannot read the tables. No secret is involved. DB_NAME defaults to the unix user's name.
  `--db NAME` dumps another DB (e.g. <project>_test after `sql/apply.sh --fresh`, to prove the replay is exact).
- file names carry the schema (api.is_admin.FUNCTION.sql vs <project>.is_admin.FUNCTION.sql).
- claude-ui's objects are left out when ./claude-ui exists: claude-ui/sql/apply.sh owns and installs them.
  CLAUDE_UI_SCHEMA (.env) defaults to DB_NAME.
- a JWT secret literal (PGRST_JWT_SECRET / JWT_SECRET from .env) that lands in DDL becomes
  current_setting('app.jwt_secret'); guarded so an empty secret can't match everything (#982).

Workflow: change the DB (psql, or write sql/migrations/<date>-<what>.sql and `psql -d $DB_NAME -f` it), then run
`python3 pg_schema_dump.py`, review `git diff sql/schema`, commit both. Never leave a live change undumped.
Exit 2 = the split lost something. Replay: sql/apply.sh (existing DB, idempotent) or sql/apply.sh --fresh (into
<project>_test). Data needed to run lives in sql/seed/, not here.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

SKIP_PATTERNS = None   # e.g. re.compile(r'shard_\d'): ephemeral objects left out of sql/schema


def generate_filename(content):
    m = re.search(r"Name: ([^;]+); Type: ([^;]+)", content)
    if not m:
        return None
    name, type_ = m.groups()
    sch = re.search(r"; Schema: ([^;]+)", content)
    schema = sch.group(1).strip() if sch and sch.group(1).strip() != "-" else ""
    fn = f"{schema}.{name}.{type_}" if schema else f"{name}.{type_}"
    fn = re.sub(r"(Name: |Type: |; |\(|\)| )", ".", fn)
    fn = re.sub(r"\.+", ".", fn)
    fn = re.sub(r"^\.", "", fn)
    fn = re.sub(r"character\.varying[^.]*\.", "cv.", fn)
    fn = re.sub(r"timestamp.with.time.zone", "tstz", fn)
    fn = re.sub(r'"', "", fn)
    fn = fn.replace("/", "_slash_").replace("*", "_star_") + ".sql"
    if len(fn.encode()) > 250:
        import hashlib
        h = hashlib.md5(fn.encode()).hexdigest()[:8]
        parts = fn.rsplit(".", 2)
        fn = (parts[0][:100] + "___" + h + "." + parts[-2] + ".sql") if len(parts) >= 3 else (fn[:200] + "___" + h + ".sql")
    return fn


def chunk_name(chunk):
    m = re.search(r"-- Name: ([^;]+);", chunk)
    return m.group(1) if m else None


def main():
    root = Path(__file__).parent.absolute()
    schema_dir = root / "sql" / "schema"
    env = {}
    envf = root / ".env"
    if envf.exists():
        for line in envf.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k] = v.strip().strip("\"'")
    import pwd
    db = env.get("DB_NAME") or pwd.getpwuid(os.getuid()).pw_name
    if "--db" in sys.argv:
        db = sys.argv[sys.argv.index("--db") + 1]
    jwt_secret = env.get("PGRST_JWT_SECRET") or env.get("JWT_SECRET", "")

    r = subprocess.run(["pg_dump", "--schema-only", "--no-owner", "-d", db], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"pg_dump failed: {r.stderr}")
    dump = "".join(l for l in r.stdout.splitlines(keepends=True)
                   if not l.startswith(("\\connect", "\\restrict", "\\unrestrict")))

    # claude-ui's objects: theirs, not ours
    owned = set()
    cui = root / "claude-ui" / "pg_schema_dump.py"
    if cui.exists():
        lst = subprocess.run([sys.executable, str(cui), "--list"], capture_output=True, text=True,
                             env={**os.environ, "DBURI": f"dbname={db}", "CLAUDE_UI_SCHEMA": env.get("CLAUDE_UI_SCHEMA") or env.get("DB_NAME") or db})
        if lst.returncode != 0:
            sys.exit(f"claude-ui --list failed: {lst.stderr}")
        owned = set(lst.stdout.split())

    def skipped(chunk):
        n = chunk_name(chunk)
        return n is not None and ((SKIP_PATTERNS is not None and SKIP_PATTERNS.search(n)) or generate_filename(chunk) in owned)

    def unsecret(text):
        return text.replace(f" '{jwt_secret}'", " current_setting('app.jwt_secret')") if jwt_secret else text

    chunks = [c for c in re.split(r"(?=^-- Name: )", dump, flags=re.MULTILINE) if c.strip()]
    schema_dir.mkdir(parents=True, exist_ok=True)
    for f in schema_dir.glob("*"):
        if f.name != ".gitignore" and not f.is_dir():
            f.unlink()

    order, kept, n_owned = [], [], 0
    for c in chunks:
        if "-- Name:" not in c:
            (schema_dir / "00").write_text(c)
            kept.append(c)
            continue
        if skipped(c):
            n_owned += 1
            continue
        fn = generate_filename(c)
        (schema_dir / fn).write_text(unsecret(c))
        order.append(fn)
        kept.append(c)
    if len(order) != len(set(order)):
        dupes = sorted({x for x in order if order.count(x) > 1})
        sys.exit(f"FILENAMES NOT UNIQUE: {dupes}")
    (schema_dir / "order.txt").write_text("\n".join(order) + "\n")

    # self-check: 00 + order.txt must rebuild the (filtered) dump exactly
    recon = (schema_dir / "00").read_text() + "".join((schema_dir / fn).read_text() for fn in order)
    if unsecret("".join(kept)) != recon:
        orig_t, rec_t = schema_dir / ".orig.tmp", schema_dir / ".recon.tmp"
        orig_t.write_text(unsecret("".join(kept))); rec_t.write_text(recon)
        d = subprocess.run(["diff", "-u", str(orig_t), str(rec_t)], capture_output=True, text=True).stdout
        print("DUMPS NOT EQUAL!\n" + d[:5000], file=sys.stderr)
        sys.exit(2)

    for f in schema_dir.glob("*.sql"):   # replayable on an existing DB
        t = f.read_text()
        t2 = re.sub(r"^CREATE (VIEW|FUNCTION)", r"CREATE OR REPLACE \1", t, flags=re.MULTILINE)
        if t2 != t:
            f.write_text(t2)
    print(f"sql/schema: {len(order)} objects written ({n_owned} claude-ui objects left to claude-ui/sql/schema)")


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# Consistent copy of the live world into a tarball (for backup.sh): save hold -> copy exactly the files/lengths BDS
# reports -> save resume, like snapshot.sh but without touching git. If the server is down, the folder is copied as-is.
#   scripts/world-backup.sh OUT.tgz          prints "<files> files, <bytes> bytes"; exit 1 on any failure
set -euo pipefail
OUT="$1"
BDS="${MC_BDS:-$HOME/mc-bds}"
WORLDS="$BDS/server/worlds"
[ -d "$WORLDS/claude_build" ] || { echo "no world at $WORLDS/claude_build"; exit 1; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

python3 - "$WORLDS" "$TMP" <<'EOF'
import json, os, shutil, socket, sys, time
worlds, dst = sys.argv[1:]
def mcs(cmd):
    s = socket.create_connection(("127.0.0.1", 8767), timeout=10); f = s.makefile("rw")
    f.write(cmd + "\n"); f.flush(); r = json.loads(f.readline()); s.close(); return r.get("lines", [])
try:
    mcs("save hold")
except OSError:
    shutil.copytree(os.path.join(worlds, "claude_build"), os.path.join(dst, "claude_build"))
    print("server not running: copied the world folder as-is", file=sys.stderr); sys.exit()
try:
    files = None
    for _ in range(60):
        lines = mcs("save query")
        if any("Data saved" in l for l in lines):
            files = [l for l in lines if "claude_build/" in l][0]; break
        time.sleep(1)
    if not files: sys.exit("save query never became ready")
    for item in files.split(", "):
        rel, n = item.rsplit(":", 1)
        src, out = os.path.join(worlds, rel), os.path.join(dst, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(src, "rb") as a, open(out, "wb") as b: b.write(a.read(int(n)))
    for extra in ("world_behavior_packs.json", "world_resource_packs.json"):   # not in the save list, but needed
        p = os.path.join(worlds, "claude_build", extra)
        if os.path.exists(p): shutil.copy(p, os.path.join(dst, "claude_build"))
finally:
    mcs("save resume")
EOF

# server settings + player lists travel with the world
for f in server.properties allowlist.json permissions.json; do
  [ -f "$BDS/server/$f" ] && cp "$BDS/server/$f" "$TMP/"
done
[ -s "$TMP/claude_build/db/CURRENT" ] && [ -s "$TMP/claude_build/level.dat" ] || { echo "copy incomplete (no CURRENT/level.dat)"; exit 1; }
tar -czf "$OUT.part" -C "$TMP" . && tar -tzf "$OUT.part" >/dev/null && mv "$OUT.part" "$OUT"
echo "$(find "$TMP" -type f | wc -l) files, $(stat -c %s "$OUT") bytes"

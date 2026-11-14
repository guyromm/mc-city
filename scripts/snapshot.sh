#!/usr/bin/env bash
# Copy the live world consistently (save hold -> copy exactly the files/lengths BDS reports -> save resume)
# plus server settings into the repo, then commit.      scripts/snapshot.sh ["commit message"]
# If the server is stopped, the world folder is copied as-is.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BDS="${MC_BDS:-$HOME/mc-bds}"
WORLDS="$BDS/server/worlds"

python3 - "$REPO" "$WORLDS" <<'EOF'
import json, os, shutil, socket, sys, time
repo, worlds = sys.argv[1:]
dst = os.path.join(repo, "world")
def mcs(cmd):
    s = socket.create_connection(("127.0.0.1", 8767), timeout=10); f = s.makefile("rw")
    f.write(cmd + "\n"); f.flush(); r = json.loads(f.readline()); s.close(); return r.get("lines", [])
shutil.rmtree(os.path.join(dst, "claude_build"), ignore_errors=True)
try:
    mcs("save hold")
except OSError:
    shutil.copytree(os.path.join(worlds, "claude_build"), os.path.join(dst, "claude_build"))
    print("server not running: copied world folder as-is"); sys.exit()
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
    # world_behavior_packs.json is not in the save list but is needed
    shutil.copy(os.path.join(worlds, "claude_build", "world_behavior_packs.json"), os.path.join(dst, "claude_build"))
    print("copied", len(files.split(", ")), "world files")
finally:
    mcs("save resume")
EOF

cp "$BDS/server/server.properties" "$REPO/bds/server.properties"
cp "$HOME/.claude/projects/-home-tv/memory/"*.md "$REPO/claude/" 2>/dev/null || true
rm -f "$REPO/claude/MEMORY.md"

cd "$REPO"
git add -A
git commit -q -m "${1:-World snapshot $(date '+%F %T')}" && git log --oneline -1 || echo "nothing changed"

#!/usr/bin/env bash
# Push edited behavior-pack scripts from the repo into the running server and hot-reload them.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BDS="${MC_BDS:-$HOME/mc-bds}"
cp -a "$REPO/bds/packs/agent_bp/." "$BDS/server/behavior_packs/agent_bp/"
python3 "$REPO/bds/mcs.py" reload
python3 "$REPO/bds/mcs.py" '{"op":"ping"}'

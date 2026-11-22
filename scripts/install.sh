#!/usr/bin/env bash
# Instantiate the "Claude Builds" server + city builder from this repo on a Linux x86_64 machine.
#   scripts/install.sh [--force-world] [--no-services]
# Idempotent. Never overwrites an existing world unless --force-world (the old one is moved aside).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BDS="${MC_BDS:-$HOME/mc-bds}"
VER="${BDS_VERSION:-1.26.63.1}"          # must match the world; Bedrock clients must be on a compatible version
FORCE=0; SERVICES=1
for a in "$@"; do case "$a" in --force-world) FORCE=1;; --no-services) SERVICES=0;; esac; done

need() { command -v "$1" >/dev/null || { echo "missing: $1 (install it first)"; exit 1; }; }
need python3; need curl; need unzip

mkdir -p "$BDS/server" "$BDS/backups" "$BDS/dl"

# 1. Bedrock Dedicated Server binary
if [ ! -x "$BDS/server/bedrock_server" ]; then
  ZIP="$BDS/dl/bedrock-server-$VER.zip"
  if [ ! -s "$ZIP" ]; then
    echo "downloading BDS $VER (by downloading you accept the Minecraft EULA / Privacy Policy)"
    curl -fL -A "Mozilla/5.0" -o "$ZIP" \
      "https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-$VER.zip"
  fi
  unzip -q -o "$ZIP" -d "$BDS/server"
  chmod +x "$BDS/server/bedrock_server"
fi
cp "$REPO/bds/server.properties" "$BDS/server/server.properties"

# 2. World
W="$BDS/server/worlds/claude_build"
if [ -d "$W" ] && [ $FORCE = 1 ]; then mv "$W" "$W.replaced-$(date +%s)"; fi
if [ ! -d "$W" ]; then
  mkdir -p "$BDS/server/worlds"; cp -a "$REPO/world/claude_build" "$W"; echo "world installed"
else
  echo "world already present at $W (use --force-world to replace it with the repo snapshot)"
fi

# 3. Behavior pack (scripting bridge) — copied into the server, source stays in the repo
rm -rf "$BDS/server/behavior_packs/agent_bp"
cp -a "$REPO/bds/packs/agent_bp" "$BDS/server/behavior_packs/agent_bp"

# 4. Link code so the repo is the live source
link() {  # link TARGET LINKPATH
  if [ -L "$2" ] || [ ! -e "$2" ]; then ln -sfn "$1" "$2"; else echo "skip: $2 exists and is not a symlink"; fi
}
for f in bds.py mcs.py leveldat.py packs; do link "$REPO/bds/$f" "$BDS/$f"; done
link "$REPO/agent" "$HOME/mc-agent"

# 5. systemd user services (server + city builder), surviving logout/reboot
if [ $SERVICES = 1 ]; then
  mkdir -p "$HOME/.config/systemd/user"
  cp "$REPO/systemd/"*.service "$HOME/.config/systemd/user/"
  systemctl --user daemon-reload
  systemctl --user enable --now mc-bds.service
  systemctl --user enable mc-city.service && systemctl --user start mc-city.service
  loginctl enable-linger "$USER" 2>/dev/null || echo "note: run 'sudo loginctl enable-linger $USER' to keep services up after logout"
fi

# 6. Claude context (optional): memory note so a new Claude Code session knows the project
MEM="$HOME/.claude/projects/-home-$USER/memory"
if [ -d "$HOME/.claude" ]; then
  mkdir -p "$MEM"; cp -n "$REPO/claude/"*.md "$MEM/" 2>/dev/null || true
  grep -q minecraft-city-project "$MEM/MEMORY.md" 2>/dev/null || \
    echo "- [Minecraft city project](minecraft-city-project.md) — Bedrock server, builders, services, control API & gotchas" >> "$MEM/MEMORY.md"
fi

echo "done. Check: systemctl --user status mc-bds mc-city ; python3 $BDS/mcs.py '{\"op\":\"ping\"}'"

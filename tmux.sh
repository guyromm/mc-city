#!/bin/bash
# minecraft (minecraft.webgma.co.il) worker registry (pattern from miko/pethelp/allocator). Created by resource-manager, #288.
#   bash tmux.sh                      (re)create the session: Claude in window "claude", then start_all
#   source tmux.sh && start <worker>  (also: stop <worker>, workers, start_all [-n = dry run], notify_claude "msg")
# Every worker is a bash `while true` loop that re-execs its one-shot command each pass. Secrets are sourced
# from .env INSIDE the loop, never expanded into these strings (argv is readable host-wide via ps).
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &>/dev/null && pwd )"
SESSION="${MINECRAFT_TMUX_SESSION:-minecraft}"
CLAUDE_TARGET="${MINECRAFT_CLAUDE_TARGET:-minecraft:claude}"
LOGDIR="$DIR/logs"; mkdir -p "$LOGDIR"
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
umask 022   # self-inspection rule (h); windows inherit the tmux SERVER's umask (0002 after the 11-12 14:24 restart), hence also in start()   # cron @reboot gives only /usr/bin:/bin; postgrest is in /usr/local/bin

PYBIN="${PYBIN:-$DIR/.venv/bin/python3}"   # venv (psycopg) for the relay + status worker; mc-city itself is stdlib-only
BDS="${MC_BDS:-$HOME/mc-bds}"   # BDS install (not in git): server/, backups/, server.log; made by scripts/install.sh
declare -A WORKERS WORKER_WINDOWS
# api: PostgREST on 127.0.0.1:$API_PORT (nginx /rest/ and api.minecraft.webgma.co.il). jwt-secret = auth.webgma.co.il's
# public RS256 keys (the only issuer, #275/13), refetched at each start by scripts/pgrst-jwks.py into ~/.pgrst-jwks.json.
WORKERS[api]="bash -c 'cd $DIR; while true; do date; set -a; source .env; set +a; $PYBIN scripts/pgrst-jwks.py; export PGRST_JWT_SECRET=@\$HOME/.pgrst-jwks.json; postgrest postgrest.conf; echo api exited, restarting in 3s; sleep 3; done'"
# ui: PRODUCTION build (adapter-node), never a public vite dev server (board #2920/#2945: every vite dev server is
# exploitable). Rebuilt at each (re)start: after editing web/, `stop ui; start ui`. Empty env plus the port only
# (doc:vite-hardening R7); never source .env here (the auth client reads only AUTH_* from it, AUTH_ENV_FILE). /map/ is served from web/map by web/src/hooks.server.js.
WORKERS[ui]="bash -c 'cd $DIR/web; while true; do date; UI=\$(grep -E ^UI_PORT= ../.env | cut -d= -f2); env -i HOME=\$HOME PATH=\$PATH LANG=C.UTF-8 npx vite build >/dev/null && env -i HOME=\$HOME PATH=\$PATH LANG=C.UTF-8 NODE_ENV=production HOST=127.0.0.1 PORT=\$UI AUTH_ENV_FILE=\$HOME/.env ORIGIN=https://minecraft.webgma.co.il node build; echo ui exited, restarting in 3s; sleep 3; done'"
# bds: bds.py runs bedrock_server + the control port 127.0.0.1:8767. The port is public, so it refuses an operator default,
# and with allow-list=false (guy 11-15: strangers welcome as visitors) anything but default visitor. It waits for a previous instance to release the control port (no two servers on one world).
# stop bds = graceful: bds.py turns the window's SIGHUP into a `stop` (world saved). Console log: ~/mc-bds/server.log.
WORKERS[bds]="bash -c 'cd $BDS; while true; do date; if [ ! -x server/bedrock_server ]; then echo no BDS installed in $BDS/server; sleep 60; continue; fi; if grep -qx default-player-permission-level=operator server/server.properties || { ! grep -qx allow-list=true server/server.properties && ! grep -qx default-player-permission-level=visitor server/server.properties; }; then echo REFUSING: server.properties: the default permission must not be operator, and must be visitor while allow-list is off; sleep 60; continue; fi; while ss -Hltn src 127.0.0.1:8767 | grep -q .; do echo waiting for the old instance to release 8767; sleep 3; done; $PYBIN -u bds.py >/dev/null; echo bds exited \$?, restarting in 10s; sleep 10; done'"
# city: the procedural city builder (MC_CITY_MAX_RING, default 6 = complete). Waits for the control API. Log: ~/mc-agent/city.log
WORKERS[city]="bash -c 'cd $HOME/mc-agent; while true; do date; until $PYBIN $BDS/mcs.py list >/dev/null 2>&1; do sleep 20; done; sleep 20; $PYBIN -u city.py run >> city.log 2>&1; echo city exited \$?, restarting in 30s; sleep 30; done'"
# status: polls the control API every 30 s into minecraft.server_status (api.server_status, the site's status card)
WORKERS[status]="bash -c 'cd $DIR; while true; do date; set -a; source .env; set +a; $PYBIN -u src/status_worker.py; echo status exited \$?, restarting in 15s; sleep 15; done'"
# xbox: MCXboxBroadcast standalone (~/mcxb, not in git: jar build 164 + config.yml + cache/ = the Xbox login token).
# Shows the server as a joinable friend session of the Xbox account mc@guyromm.com, so console players (PS/Xbox/Switch,
# no "Add Server" there) add that account as a friend and join from the Friends tab. Re-login: the log prints a
# microsoft.com/link code. Java = ~/.local/bin/java (Temurin 21 JRE).
# -Xmx256m (self-inspection 11-25): without it the JVM may grow to 1/4 of RAM (16 GB); RSS rose 120->163 MB in 2 days.
WORKERS[xbox]="bash -c 'cd $HOME/mcxb; while true; do date; java -Xmx256m -jar MCXboxBroadcastStandalone.jar < /dev/null; echo xbox exited \$?, restarting in 30s; sleep 30; done'"
# map: scripts/render-map.sh (uNmINeD) -> web/static/map/ = https://minecraft.webgma.co.il/map/, every MAP_EVERY s (1 h)
WORKERS[map]="bash -c 'cd $DIR; while true; do date; PYBIN=$PYBIN bash scripts/render-map.sh || echo map render FAILED; sleep \${MAP_EVERY:-3600}; done'"
# claude-ui registers its own workers (voice-relay) and notify_claude
source "$DIR/claude-ui/tmux.sh"
workers(){ for w in "${!WORKERS[@]}"; do echo "$w"; done | sort; }

start() {
    local w="$1"; [ -n "${WORKERS[$w]}" ] || { echo "no worker '$w'"; return 1; }
    tmux has-session -t "$SESSION" 2>/dev/null || create_claude
    tmux kill-window -t "$SESSION:w-$w" 2>/dev/null
    tmux new-window -d -t "$SESSION" -n "w-$w" "umask 022; bash -c '${WORKERS[$w]//\'/\'\\\'\'} 2>&1 | tee -a $LOGDIR/$w.log'"
    echo "started $w in $SESSION:w-$w (log: logs/$w.log)"
}
stop() { tmux kill-window -t "$SESSION:w-$1" 2>/dev/null && echo "stopped $1"; }
# start_all = every worker in WORKERS minus this opt-out list (one-line reason each); a new worker starts by default
WORKER_OPTOUT=(
)
start_all() {
    local w; for w in $(workers); do
        [[ " ${WORKER_OPTOUT[*]} " == *" $w "* ]] && { echo "skip $w (opt-out)"; continue; }
        if [ "$1" = "-n" ]; then echo "would start $w"; else start "$w"; fi
    done
}

# The Claude session in window "claude" (pane title locked so the board watcher's target stays stable).
create_claude() {
    tmux has-session -t "$SESSION" 2>/dev/null && return 0
    tmux -u new-session -d -s "$SESSION" -n claude -c "$DIR"
    tmux set-option -p -t "$SESSION:claude" allow-set-title off 2>/dev/null   # tmux >= 3.4
    tmux select-pane -t "$SESSION:claude" -T claude
    command -v board >/dev/null && { board watch-start || true; }   # board watcher -> $SESSION:claude
    tmux send-keys -t "$SESSION:claude" "cd '$DIR' && claude --continue --dangerously-skip-permissions || claude --dangerously-skip-permissions" C-m
}

notify_claude() {
    tmux send-keys -t "$CLAUDE_TARGET" -l "[worker] $*" 2>/dev/null && sleep 0.3 && tmux send-keys -t "$CLAUDE_TARGET" Enter
}

# Run-as-script check: `(return 0)` succeeds only when SOURCED. The old test, BASH_SOURCE[0] == $0, was ALSO true for
# `bash -c 'source "$0"' tmux.sh`, which is how workers called notify_claude: on 2026-11-12 14:02 that killed the whole
# auth tmux session (Claude included). `if`, not `&&`: a false test must not become the file's exit status (@reboot).
if ! (return 0 2>/dev/null); then tmux kill-session -t "$SESSION" 2>/dev/null; create_claude; start_all; fi
true

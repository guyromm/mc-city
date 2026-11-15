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

declare -A WORKERS
# (no workers yet: add WORKERS[name]="..." lines here, e.g. the PostgREST api on $API_PORT)
workers() { for w in "${!WORKERS[@]}"; do echo "$w"; done | sort; }

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

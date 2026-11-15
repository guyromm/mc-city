#!/usr/bin/env python3
"""Poll the mc-city control API (127.0.0.1:8767) and keep minecraft.server_status current for the web UI.

Runs forever, one check every STATUS_EVERY seconds (default 30); exits non-zero on a DB error so the tmux loop
restarts it. A dead BDS is not an error: it is written as online=false.

Also keeps the operators: BDS keys permissions.json by xuid, known only once a player has connected, so every name in
MC_OPERATORS (comma-separated, from .env) that shows up in a "Player connected: NAME, xuid: X" line is written into
permissions.json as operator and applied with `permission reload`.
"""
import json, os, re, socket, sys, time
from pathlib import Path
import psycopg

EVERY = int(os.environ.get("STATUS_EVERY", "30"))
HOME = Path.home()
STATE = HOME / "agent/city/state.json"
PROPS = HOME / "mc-bds/server/server.properties"
SERVER_LOG = HOME / "mc-bds/server.log"
PERMS = HOME / "mc-bds/server/permissions.json"
OPERATORS = {n.strip().lower() for n in os.environ.get("MC_OPERATORS", "").split(",") if n.strip()}


def mcs(*reqs, timeout=10):
    """Send requests (raw console lines or dicts) to bds.py; return the parsed replies."""
    with socket.create_connection(("127.0.0.1", 8767), timeout=timeout) as s:
        f = s.makefile("rw")
        out = []
        for r in reqs:
            f.write((json.dumps(r) if isinstance(r, dict) else r) + "\n"); f.flush()
            out.append(json.loads(f.readline()))
        return out


def prop(name):
    try:
        for line in PROPS.read_text().splitlines():
            if line.startswith(name + "="): return line.split("=", 1)[1].strip()
    except OSError:
        pass


def version():
    try:   # "Version: 1.26.63.1" near the top of the newest start in server.log
        with SERVER_LOG.open("rb") as f:
            f.seek(max(0, SERVER_LOG.stat().st_size - 2_000_000))
            hits = re.findall(rb"Version: ([0-9.]+)", f.read())
        return hits[-1].decode() if hits else None
    except OSError:
        return None


def plots():
    try: return len(json.loads(STATE.read_text()).get("built", {}))
    except (OSError, ValueError): return None


def sync_operators():
    if not OPERATORS: return
    try:
        with SERVER_LOG.open("rb") as f:
            f.seek(max(0, SERVER_LOG.stat().st_size - 2_000_000))
            seen = {m[1].decode(): m[0].decode() for m in re.findall(rb"Player connected: ([^,\n]+), xuid: (\d+)", f.read())}
        perms = json.loads(PERMS.read_text() or "[]")
    except (OSError, ValueError):
        return
    have = {p.get("xuid") for p in perms if p.get("permission") == "operator"}
    add = [(x, n) for x, n in seen.items() if n.lower() in OPERATORS and x not in have]
    if not add: return
    perms = [p for p in perms if p.get("xuid") not in {x for x, _ in add}] + [{"permission": "operator", "xuid": x} for x, _ in add]
    PERMS.write_text(json.dumps(perms, indent=2) + "\n")
    try:
        mcs("permission reload")
    except OSError:
        pass   # applied at the next start anyway
    print("operator:", ", ".join(f"{n} ({x})" for x, n in add), flush=True)


def check():
    try:
        ping, players, tour = mcs({"op": "ping"}, {"op": "players"}, {"op": "tour_status"})
        if not ping.get("ok"): raise OSError(f"ping: {ping}")
        return dict(online=True, players=players.get("result") or [], tour=tour.get("result"))
    except (OSError, ValueError) as e:
        return dict(online=False, players=[], tour=None)


def main():
    with psycopg.connect(os.environ.get("DBURI", "postgresql:///minecraft"), autocommit=True) as db:
        while True:
            st = check()
            sync_operators()
            db.execute("""UPDATE minecraft.server_status SET online=%(online)s, players=%(players)s, tour=%(tour)s,
                            version=coalesce(%(version)s, version), max_players=%(max)s, plots_built=%(plots)s,
                            online_since=CASE WHEN NOT %(online)s THEN NULL WHEN online THEN online_since ELSE now() END,
                            checked_at=now()""",
                       dict(online=st["online"], players=json.dumps(st["players"]), tour=json.dumps(st["tour"]),
                            version=version(), max=int(prop("max-players") or 0) or None, plots=plots()))
            time.sleep(EVERY)


if __name__ == "__main__":
    main()

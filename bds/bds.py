#!/usr/bin/env python3
"""Run bedrock_server and expose a control port (TCP 127.0.0.1:8767, newline-delimited).

Request line formats:
  raw console command, e.g.  say hello      -> {"lines":[...output lines within ~0.4s...]}
  JSON  {"op":"scan", ...args}              -> script reply {"ok":true,"result":...}
"""
import asyncio, json, os, sys, itertools, time

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "server")
LOG = os.path.join(HERE, "server.log")
EVENTS = os.path.join(HERE, "events.log")
ids = itertools.count(1)
pending = {}          # id -> future
listeners = set()     # queues receiving every stdout line
proc = None

async def pump():
    with open(LOG, "a") as log:
        while line := await proc.stdout.readline():
            s = line.decode(errors="replace").rstrip("\n")
            log.write(s + "\n"); log.flush()
            try: print(s, flush=True)
            except OSError: pass   # stdout gone (tmux window closed): server.log still has it
            i = s.find("AGENT ")
            if i >= 0:
                _, rid, payload = s[i:].split(" ", 2)
                if rid in pending:
                    pending.pop(rid).set_result(json.loads(payload))
                    continue
                with open(EVENTS, "a") as ev:
                    ev.write(json.dumps({"t": time.time(), "id": rid, **json.loads(payload)}) + "\n")
            for q in list(listeners):
                q.put_nowait(s)
    print("server exited", flush=True)
    os._exit(proc.returncode or 0)

async def send(cmd):
    proc.stdin.write((cmd + "\n").encode()); await proc.stdin.drain()

async def handle(line):
    if line.startswith("{"):
        req = json.loads(line)
        op = req.pop("op")
        rid = str(next(ids)); req["id"] = rid
        fut = asyncio.get_running_loop().create_future(); pending[rid] = fut
        await send(f"scriptevent agent:{op} {json.dumps(req, separators=(',', ':'))}")
        try:
            return await asyncio.wait_for(fut, 30)
        except asyncio.TimeoutError:
            pending.pop(rid, None); return {"error": "timeout"}
    q = asyncio.Queue(); listeners.add(q)
    await send(line)
    lines = []
    try:
        while True:
            lines.append(await asyncio.wait_for(q.get(), 0.4))
    except asyncio.TimeoutError:
        pass
    finally:
        listeners.discard(q)
    return {"lines": lines}

async def on_ctl(reader, writer):
    while raw := await reader.readline():
        line = raw.decode().strip()
        if not line: continue
        try: res = await handle(line)
        except Exception as e: res = {"error": repr(e)}
        writer.write((json.dumps(res) + "\n").encode()); await writer.drain()
    writer.close()

async def main():
    global proc
    proc = await asyncio.create_subprocess_exec(
        "./bedrock_server", cwd=SERVER, env={**os.environ, "LD_LIBRARY_PATH": "."},
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        start_new_session=True)   # own session: a closing tmux pane's SIGHUP must not kill it unsaved
    import signal
    loop = asyncio.get_running_loop()
    # TERM/INT (systemd, ^C) and HUP (tmux kill-window) all become a graceful "stop": the world is saved, then pump() exits
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        loop.add_signal_handler(sig, lambda: asyncio.ensure_future(send("stop")))
    srv = await asyncio.start_server(on_ctl, "127.0.0.1", 8767)
    print("control port 127.0.0.1:8767", flush=True)
    await asyncio.gather(pump(), srv.serve_forever())

asyncio.run(main())

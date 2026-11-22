#!/usr/bin/env python3
"""Bridge: Minecraft Bedrock client (/connect) <-> local control port.
Game connects to ws://localhost:8765. Control: TCP localhost:8766, one command per line,
one JSON reply per line. Events are appended to events.log."""
import asyncio, json, uuid, websockets, time, os
HERE = os.path.dirname(os.path.abspath(__file__))
game = None
pending = {}
def msg(purpose, body):
    rid = str(uuid.uuid4())
    return rid, json.dumps({"header": {"version": 1, "requestId": rid, "messageType": "commandRequest",
                                       "messagePurpose": purpose}, "body": body})
async def on_game(ws, *_):
    global game
    game = ws
    print("game connected", flush=True)
    for ev in ("PlayerMessage",):
        await ws.send(msg("subscribe", {"eventName": ev})[1])
    try:
        async for raw in ws:
            m = json.loads(raw)
            rid = m.get("header", {}).get("requestId")
            if rid in pending:
                pending.pop(rid).set_result(m.get("body"))
            else:
                with open(os.path.join(HERE, "events.log"), "a") as f:
                    f.write(json.dumps({"t": time.time(), **m}) + "\n")
    finally:
        game = None
        print("game disconnected", flush=True)
async def run_cmd(line):
    if game is None:
        return {"error": "game not connected"}
    rid, payload = msg("commandRequest", {"version": 1, "commandLine": line, "origin": {"type": "player"}})
    fut = asyncio.get_running_loop().create_future()
    pending[rid] = fut
    await game.send(payload)
    try:
        return await asyncio.wait_for(fut, 10)
    except asyncio.TimeoutError:
        pending.pop(rid, None)
        return {"error": "timeout"}
async def on_ctl(reader, writer):
    while line := (await reader.readline()).decode().strip():
        writer.write((json.dumps(await run_cmd(line)) + "\n").encode())
        await writer.drain()
    writer.close()
async def main():
    async with websockets.serve(on_game, "127.0.0.1", 8765, max_size=None):
        srv = await asyncio.start_server(on_ctl, "127.0.0.1", 8766)
        print("listening ws:8765 ctl:8766", flush=True)
        await srv.serve_forever()
asyncio.run(main())

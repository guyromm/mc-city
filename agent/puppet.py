"""Shared feeder: stream fill jobs to the in-game puppet builder and wait until done."""
import json, math, time
from tower import Conn, boxes

def layered_jobs(m, cx, cz):
    """Solid boxes one y-layer at a time, swept by angle around (cx, cz); air boxes last per layer."""
    jobs = []
    for y in sorted({p[1] for p in m.v}):
        solid = {p: v for p, v in m.v.items() if p[1] == y and v[0] != "air"}
        air = {p: v for p, v in m.v.items() if p[1] == y and v[0] == "air"}
        bx = boxes(solid) + boxes(air)
        bx.sort(key=lambda b: (b[6][0] == "air",
                               (math.degrees(math.atan2((b[2] + b[5]) / 2 - cz, (b[0] + b[3]) / 2 - cx)) + 360) % 360))
        for (x1, y1, z1, x2, y2, z2, (b, st)) in bx:
            jobs.append([x1, y1, z1, x2, y2, z2, b] + ([json.loads(st)] if st else []))
    return jobs

def run(jobs, player, speed, center, setup=()):
    c = Conn()
    for cmd in setup: c.req(cmd)
    c.req(f"gamemode creative {player}"); c.req(f"ability {player} mayfly true")
    i, t0, first = 0, time.time(), True
    while True:
        st = c.req({"op": "job_status"})["result"]
        if i < len(jobs) and st["queued"] < 60:
            batch, size = [], 0
            while i < len(jobs) and size < 1400:
                batch.append(jobs[i]); size += len(json.dumps(jobs[i])); i += 1
            args = {"op": "job_add", "items": batch}
            if first: args.update(player=player, speed=speed, center=list(center)); first = False
            c.req(args); continue
        if i >= len(jobs) and st["queued"] == 0 and not st["active"]: break
        print(f"[{time.time() - t0:5.0f}s] {st['done']}/{len(jobs)} jobs errors={st['errors'][-1:]}", flush=True)
        time.sleep(5)
    print("build finished in %.0fs" % (time.time() - t0), flush=True)
    return c

def verify(c, m, x1, x2, z1, z2):
    bad = []
    for y in sorted({p[1] for p in m.v}):
        for zs in range(z1, z2 + 1, 16):      # scan in strips to keep replies small
            ze = min(zs + 15, z2)
            r = c.req({"op": "scan", "from": [x1, y, zs], "to": [x2, y, ze]})["result"]
            pal, rows = r["palette"], r["layers"][0]
            for zi, row in enumerate(rows):
                x = x1
                for run_ in row.split(","):
                    idx, _, n = run_.partition("*")
                    for _ in range(int(n or 1)):
                        want = m.v.get((x, y, zs + zi))
                        got = pal[int(idx)].split("{")[0]
                        if want and got != want[0]: bad.append(((x, y, zs + zi), want[0], got))
                        x += 1
    return bad

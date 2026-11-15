#!/usr/bin/env python3
"""Rotunda Library east of the Atrium Tower, built by puppeteering a real player.

  rotunda.py plan [k]                 ASCII plan of storey k (+1 and +2 layers)
  rotunda.py build PLAYER [speed]     queue the build for PLAYER, stream jobs, report progress
  rotunda.py verify                   scan & diff all solid blocks
"""
import json, math, sys, time
from tower import Model, boxes, Conn, G, H, ASC, GLYPH

CX, CZ = 46, 0          # centre
RO = 12.5               # outer wall radius
NS = 6                  # storeys
COL = 2.5               # central column radius
SP_IN, SP_OUT = 2.5, 4.6  # spiral stair annulus
STEP_DEG = 18           # 10 half-steps per storey = 180 deg per storey
BRIDGE_K = 2            # skybridge storey
SETUP = ["tickingarea add 28 -64 -16 62 0 16 rotunda true"]

def yb(k): return G + H * k

def polar(x, z):
    dx, dz = x - CX, z - CZ
    return math.hypot(dx, dz), (math.degrees(math.atan2(dz, dx)) + 360) % 360

def spiral_surface(x, z):
    """Walking-surface height (in half blocks above G+1 base) for a stair cell, or None."""
    r, a = polar(x, z)
    if not (SP_IN <= r < SP_OUT): return None
    return a  # angle only; the step index depends on turn number

def step_blocks():
    """Return {(x,y,z): (block, states)} for the whole helix and the set of cells cut from slabs."""
    cells = {}
    total = NS * 10          # half steps to reach the roof slab
    for i in range(total):
        a0, a1 = (i * STEP_DEG) % 360, (i * STEP_DEG) % 360 + STEP_DEG
        y = G + 1 + i // 2
        half = i % 2 == 0    # even: bottom slab at y (surface y+0.5); odd: full block (surface y+1)
        for x in range(CX - 5, CX + 6):
            for z in range(CZ - 5, CZ + 6):
                r, a = polar(x, z)
                if not (SP_IN <= r < SP_OUT): continue
                if not (a0 <= a < a1 or a0 <= a + 360 < a1): continue
                cells[(x, y, z)] = ("smooth_sandstone_slab", {"minecraft:vertical_half": "bottom"}) if half else ("smooth_sandstone", None)
                # support underneath odd steps' slab partner is not needed (blocks float)
    return cells

def build(m):
    steps = step_blocks()
    # which cells of the annulus need a slab hole (head clearance) on storey slab k
    def hole(k, x, z):
        ys = yb(k)
        for (sx, sy, sz), (b, _) in steps.items():
            if sx == x and sz == z:
                surf = sy + (0.5 if "slab" in b else 1.0)
                if ys - 2.2 < surf <= ys + 1 and sy != ys: return True
        return False
    hole_cache = {}
    for k in range(NS + 1):
        y0 = yb(k)
        roof = k == NS
        floor = ["polished_deepslate", "dark_oak_planks", "dark_oak_planks", "spruce_planks", "spruce_planks", "birch_planks", "cut_sandstone"][k]
        for x in range(CX - 13, CX + 14):
            for z in range(CZ - 13, CZ + 14):
                r, a = polar(x, z)
                if r > RO: continue
                b = floor
                if r > RO - 1: b = "cut_red_sandstone"                       # slab edge band
                elif r < COL: b = "chiseled_sandstone"
                elif SP_IN <= r < SP_OUT and k > 0:
                    key = (k, x, z)
                    if key not in hole_cache: hole_cache[key] = hole(k, x, z)
                    if hole_cache[key]: continue
                elif k == 4 and 6 <= r < 9 and not (min(a % 90, 90 - a % 90) < 8):
                    continue                                                 # gallery void (double height 3-4)
                elif not roof and k > 0 and int(round(r)) == 10 and int(a) % 45 < 6:
                    b = "glowstone"
                m.set(x, y0, z, b)
                if roof: continue
                # central column
                if r < COL:
                    for dy in range(1, H): m.set(x, y0 + dy, z, "sandstone" if dy != 2 else "chiseled_sandstone")
                # outer wall with windows & pilasters every 30 degrees
                if RO - 1 < r <= RO:
                    pil = min(a % 30, 30 - a % 30) < 4
                    for dy in range(1, H):
                        if pil: wb = "cut_sandstone"
                        elif k == 0: wb = "glass" if dy in (1, 2, 3) else "smooth_sandstone"
                        elif k == NS - 1: wb = "glass" if dy in (1, 2, 3) else "smooth_sandstone"
                        else: wb = "glass" if dy in (2, 3) else "smooth_sandstone"
                        m.set(x, y0 + dy, z, wb)
        if roof: continue
        # interior per storey
        for x in range(CX - 13, CX + 14):
            for z in range(CZ - 13, CZ + 14):
                r, a = polar(x, z)
                if k == 1 and 6 <= r < 10.5 and min(a % 30, 30 - a % 30) < 2.5 and not (80 < a < 100):
                    for dy in (1, 2, 3): m.set(x, y0 + dy, z, "bookshelf")          # radial stacks
                if k == 2 and 7.5 <= r < 8.5 and int(a) % 40 < 12:
                    m.set(x, y0 + 1, z, "spruce_slab", {"minecraft:vertical_half": "top"})  # reading desks
                if k == 3 and 10.4 <= r < 11.4 and not (165 < a < 195):
                    for dy in (1, 2): m.set(x, y0 + dy, z, "bookshelf")              # wall shelves
                if k == 4 and (5.2 <= r < 6 or 9 <= r < 9.8) and not (min(a % 90, 90 - a % 90) < 8):
                    m.set(x, y0 + 1, z, "glass_pane")                              # gallery railing
                if k == 5 and 7 <= r < 8 and int(a) % 60 < 8:
                    m.set(x, y0 + 1, z, "lectern")
        # entrance (south, z+) on ground floor
        if k == 0:
            for x in range(CX - 1, CX + 2):
                for dy in (1, 2, 3):
                    for z in range(CZ + 11, CZ + 14): m.v.pop((x, y0 + dy, z), None)
            m.box(CX - 2, y0 + 4, CZ + 12, CX + 2, y0 + 4, CZ + 12, "chiseled_red_sandstone")
        if k == BRIDGE_K:
            for z in (0, 1):
                for dy in (1, 2):
                    for x in range(CX - 13, CX - 10): m.v.pop((x, y0 + dy, z), None)
    # helix last so it overrides floors/holes
    for p, (b, st) in steps.items():
        m.set(*p, b, st)
    # dome
    yr = yb(NS)
    for x in range(CX - 13, CX + 14):
        for z in range(CZ - 13, CZ + 14):
            for dy in range(1, 14):
                d = math.sqrt((x - CX) ** 2 + (z - CZ) ** 2 + (dy * 1.0) ** 2)
                if RO - 1.1 < d <= RO:
                    _, a = polar(x, z)
                    m.set(x, yr + dy, z, "glass" if (int(a) % 45 < 22 and dy < 10) else "waxed_oxidized_copper")
    m.set(CX, yr + 13, CZ, "lightning_rod")
    # skybridge from Atrium Tower east facade (x=16) to rotunda (x~34), storey 2
    yB = yb(BRIDGE_K)
    for x in range(16, CX - 10):
        m.set(x, yB, 0, "smooth_quartz"); m.set(x, yB, 1, "smooth_quartz")
        if x == 16:
            for dy in (1, 2):
                for z in (0, 1): m.set(x, yB + dy, z, "air")
            continue
        for dy in (1, 2, 3):
            m.set(x, yB + dy, -1, "glass"); m.set(x, yB + dy, 2, "glass")
        m.set(x, yB + 4, 0, "glass"); m.set(x, yB + 4, 1, "glass")
        m.set(x, yB, -1, "quartz_pillar"); m.set(x, yB, 2, "quartz_pillar")
        m.set(x, yB + 4, -1, "quartz_pillar"); m.set(x, yB + 4, 2, "quartz_pillar")
    return m

def layered_jobs(m):
    """Solid boxes, one y-layer at a time, ordered by angle around the centre (spiral sweep)."""
    jobs = []
    ys = sorted({p[1] for p in m.v})
    for y in ys:
        layer = {p: v for p, v in m.v.items() if p[1] == y and v[0] != "air"}
        air = {p: v for p, v in m.v.items() if p[1] == y and v[0] == "air"}
        bx = boxes(layer) + boxes(air)
        def ang(b):
            cx, cz = (b[0] + b[3]) / 2, (b[2] + b[5]) / 2
            return (b[6][0] == "air", (math.degrees(math.atan2(cz - CZ, cx - CX)) + 360) % 360)
        bx.sort(key=ang)
        for (x1, y1, z1, x2, y2, z2, (b, st)) in bx:
            jobs.append([x1, y1, z1, x2, y2, z2, b] + ([json.loads(st)] if st else []))
    return jobs

def plan(m, k, dy):
    y = yb(k) + dy
    print(f"--- rotunda storey {k} y={y} ---")
    for z in range(CZ - 13, CZ + 14):
        print("".join(GLYPH.get(m.v[(x, y, z)][0], m.v[(x, y, z)][0][0]) if (x, y, z) in m.v else "." for x in range(CX - 13, CX + 14)))

if __name__ == "__main__":
    m = build(Model())
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if cmd == "plan":
        k = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        plan(m, k, 0); plan(m, k, 1); plan(m, k, 2); sys.exit()
    c = Conn()
    if cmd == "build":
        player = sys.argv[2]; speed = float(sys.argv[3]) if len(sys.argv) > 3 else 0.9
        jobs = layered_jobs(m)
        print(f"{len(jobs)} jobs, {sum(1 for v in m.v.values() if v[0] != 'air')} blocks", flush=True)
        c.req("tickingarea add 28 -64 -16 62 0 16 rotunda true")
        c.req(f"gamemode creative {player}")
        c.req(f"ability {player} mayfly true")
        i, t0 = 0, time.time()
        first = True
        while True:
            st = c.req({"op": "job_status"})["result"]
            if i < len(jobs) and st["queued"] < 60:
                batch, size = [], 0
                while i < len(jobs) and size < 1400:
                    batch.append(jobs[i]); size += len(json.dumps(jobs[i])); i += 1
                args = {"op": "job_add", "items": batch}
                if first: args.update(player=player, speed=speed, center=[CX + 0.5, CZ + 0.5]); first = False
                c.req(args)
                continue
            if i >= len(jobs) and st["queued"] == 0 and not st["active"]:
                break
            print(f"[{time.time() - t0:5.0f}s] {st['done']}/{len(jobs)} jobs  errors={st['errors'][-1:] }", flush=True)
            time.sleep(5)
        print("build finished in %.0fs" % (time.time() - t0))
        cmd = "verify"
    if cmd == "verify":
        bad = 0
        for y in sorted({p[1] for p in m.v}):
            r = c.req({"op": "scan", "from": [CX - 13, y, -13], "to": [CX + 13, y, 13]})["result"]
            pal, rows = r["palette"], r["layers"][0]
            for zi, row in enumerate(rows):
                x = CX - 13
                for run in row.split(","):
                    idx, _, n = run.partition("*")
                    for _ in range(int(n or 1)):
                        want = m.v.get((x, y, -13 + zi))
                        if want and pal[int(idx)].split("{")[0] != want[0]:
                            bad += 1
                            if bad <= 5: print("mismatch", (x, y, -13 + zi), want[0], pal[int(idx)])
                        x += 1
        # bridge part outside the scanned window
        print(f"verify: {bad} mismatches")

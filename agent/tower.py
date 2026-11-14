#!/usr/bin/env python3
"""Atrium Tower: a 5-storey building with a central atrium, two switchback stair cores,
per-floor layouts, setback terraces on the top floor and a roof garden.

  tower.py plan            -> print ASCII plans per storey
  tower.py build [k ...]   -> build storeys (default all), verify each by scanning
  tower.py verify [k ...]  -> scan & diff only
"""
import json, socket, sys
from collections import defaultdict

# ---------------------------------------------------------------- geometry
G = -61            # ground slab y (replaces grass layer)
H = 5              # storey height (slab + 4 air)
N = 5              # storeys
R = 16             # outer wall at |x|,|z| == R
ATR = 3            # atrium hole |x|,|z| <= ATR on slabs 1..N
RAIL = 4           # railing ring
CW = 8             # corridor wall ring (corridor is ring 4..7)
E = "minecraft:"

def yb(k): return G + H * k  # slab y of storey k

# stair direction states (bedrock weirdo_direction: 0 east,1 west,2 south,3 north = ascending toward)
ASC = {"+x": 0, "-x": 1, "+z": 2, "-z": 3}

class Model:
    def __init__(s): s.v = {}
    def set(s, x, y, z, b, st=None): s.v[(x, y, z)] = (b, json.dumps(st, sort_keys=True) if st else "")
    def box(s, x1, y1, z1, x2, y2, z2, b, st=None):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    s.set(x, y, z, b, st)
    def get(s, x, y, z): return s.v.get((x, y, z), ("air", ""))[0]

def ring(x, z): return max(abs(x), abs(z))

def footprint(k, x, z):
    """True if (x,z) is inside storey k's floor area (incl. outer wall)."""
    if ring(x, z) > R: return False
    if k == N - 1:  # top floor: NW and SE corner squares are terraces
        if (x <= -CW - 1 and z <= -CW - 1) or (x >= CW + 1 and z >= CW + 1): return False
    return True

def corner_core(x, z):
    """Map (x,z) into core-local coords if in NE (x>,z<) or SW (x<,z>) core square, else None.
    Local frame: u = across lanes (0..6), w = along run (0 near hall .. 6 far)."""
    if x >= CW + 1 and z <= -CW - 1:   # NE
        return (x - (CW + 1), -(z + CW + 1), "NE")
    if x <= -CW - 1 and z >= CW + 1:   # SW
        return (-x - (CW + 1), z - (CW + 1), "SW")
    return None

def core_world(u, w, which):
    if which == "NE": return (u + CW + 1, -(w + CW + 1))
    return (-(u + CW + 1), w + CW + 1)

# ---------------------------------------------------------------- per-storey design
def build_storey(m, k):
    y0 = yb(k)
    top = k == N  # roof level "storey"
    floor_mat = ["polished_andesite", "oak_planks", "birch_planks", "spruce_planks", "smooth_quartz"][k] if not top else "smooth_stone"

    # 1) clear the whole storey volume (slab + 4 air) within footprint bbox
    for x in range(-R, R + 1):
        for z in range(-R, R + 1):
            for y in range(y0, y0 + H):
                m.set(x, y, z, "air")

    # 2) slab
    for x in range(-R, R + 1):
        for z in range(-R, R + 1):
            if not (footprint(k, x, z) or (top and footprint(N - 1, x, z)) or (k == N - 1 and ring(x, z) <= R)):
                continue
            if k == N - 1 and not footprint(k, x, z):   # terrace deck on slab of top floor
                m.set(x, y0, z, "spruce_planks"); continue
            if top and not footprint(N - 1, x, z):
                continue  # above terraces: open sky
            b = floor_mat
            if ring(x, z) == R: b = "light_gray_concrete"           # slab edge band
            elif k > 0 and ring(x, z) <= ATR:
                b = "glass" if top else "air"                        # atrium hole / skylight
            elif not top and (x % 4 == 2) and (z % 4 == 2) and ring(x, z) >= CW + 2:
                b = "sea_lantern"                                    # lights embedded in slab
            m.set(x, y0, z, b)
    if k == 0:  # atrium garden on ground floor
        for x in range(-ATR, ATR + 1):
            for z in range(-ATR, ATR + 1):
                m.set(x, y0, z, "grass_block")
        m.set(0, y0 + 1, 0, "flowering_azalea")
        for (x, z) in [(-2, -2), (2, 2), (-2, 2), (2, -2)]:
            m.set(x, y0 + 1, z, "fern")
        m.box(-ATR - 1, y0, -ATR - 1, ATR + 1, y0, -ATR - 1, "mossy_stone_bricks")
        m.box(-ATR - 1, y0, ATR + 1, ATR + 1, y0, ATR + 1, "mossy_stone_bricks")
        m.box(-ATR - 1, y0, -ATR - 1, -ATR - 1, y0, ATR + 1, "mossy_stone_bricks")
        m.box(ATR + 1, y0, -ATR - 1, ATR + 1, y0, ATR + 1, "mossy_stone_bricks")

    if top:
        roof(m, y0); return

    # 3) atrium railing (storeys >= 1)
    if k >= 1:
        for x in range(-RAIL, RAIL + 1):
            for z in range(-RAIL, RAIL + 1):
                if ring(x, z) == RAIL: m.set(x, y0 + 1, z, "glass_pane")

    # 4) outer walls / facade
    for x in range(-R, R + 1):
        for z in range(-R, R + 1):
            if not footprint(k, x, z): continue
            on_edge = ring(x, z) == R or (k == N - 1 and (
                (x == -CW and z <= -CW) or (z == -CW and x <= -CW) or (x == CW and z >= CW) or (z == CW and x >= CW)))
            if not on_edge: continue
            corner = (abs(x) == R and abs(z) == R)
            pillar = corner or (x % 4 == 0 and z % 4 == 0) or (abs(x) == R and z % 4 == 0) or (abs(z) == R and x % 4 == 0)
            for dy in range(1, H):
                y = y0 + dy
                if pillar: b = "quartz_pillar"
                elif k == 0: b = "glass"                      # storefront
                elif dy in (2, 3): b = "glass"
                else: b = "white_concrete"
                m.set(x, y, z, b)
    if k == 0:  # main entrance on south facade
        m.box(-2, y0 + 1, R, 2, y0 + 3, R, "air")
        m.box(-3, y0 + 4, R, 3, y0 + 4, R, "quartz_block")

    # 5) corridor wall (ring CW) with doorways, storeys >= 1 ; ground floor gets columns instead
    for x in range(-CW, CW + 1):
        for z in range(-CW, CW + 1):
            if ring(x, z) != CW or not footprint(k, x, z): continue
            if k == 0:
                if x % 4 == 0 and z % 4 == 0:
                    m.box(x, y0 + 1, z, x, y0 + 4, z, "quartz_pillar")
                continue
            door = (abs(x) == CW and z in (-6, -1, 5)) or (abs(z) == CW and x in (-5, 1, 6))
            for dy in range(1, H):
                b = "air" if door and dy <= 2 else ("glass" if dy == 2 and k == 1 else "white_concrete")
                m.set(x, y0 + dy, z, b)

    # 6) radial room partitions in the side wings (between ring CW and R), storeys >= 1
    if k >= 1:
        top_floor = k == N - 1
        splits = {1: [-4, 2], 2: [-4, -1, 3], 3: [0], 4: []}[k]
        for s in splits:
            for t in range(CW + 1, R):
                for (x, z) in [(t, s), (-t, -s), (s, -t), (-s, t)]:   # rotate around the 4 wings
                    if footprint(k, x, z) and not corner_core(x, z):
                        for dy in range(1, H): m.set(x, y0 + dy, z, "white_concrete")
                # doorway between neighbouring rooms near the outer side? keep rooms separate
        # walls separating corner squares from wings
        core_sep = [(t, -CW) for t in range(CW + 1, R)] + [(CW, -t) for t in range(CW + 1, R)] + \
                   [(-t, CW) for t in range(CW + 1, R)] + [(-CW, t) for t in range(CW + 1, R)]
        room_sep = [(-t, -CW) for t in range(CW + 1, R)] + [(-CW, -t) for t in range(CW + 1, R)] + \
                   [(t, CW) for t in range(CW + 1, R)] + [(CW, t) for t in range(CW + 1, R)]
        for (x, z) in core_sep + ([] if top_floor else room_sep):   # top floor: corner squares are terraces
            if footprint(k, x, z):
                for dy in range(1, H): m.set(x, y0 + dy, z, "white_concrete")
        # stair cores open into their hall room (hall row w=0, lane A side)
        for (x, z) in [(10, -CW), (-10, CW)]:
            m.box(x, y0 + 1, z, x, y0 + 2, z, "air")
        # corner rooms (NW, SE) get a doorway into the wing room next to them
        if not top_floor:
            for (x, z) in [(-12, -CW), (12, CW)]:
                m.box(x, y0 + 1, z, x, y0 + 2, z, "air")
        if top_floor:
            # terrace railings
            for x in range(-R, R + 1):
                for z in range(-R, R + 1):
                    if not footprint(k, x, z) and ring(x, z) == R:
                        m.set(x, y0 + 1, z, "spruce_fence")
            for (x, z) in [(-12, -12), (12, 12)]:
                m.set(x, y0 + 1, z, "flowering_azalea")
            # terrace doors in the setback walls
            for (x, z) in [(-12, -CW), (-CW, -12), (12, CW), (CW, 12)]:
                m.box(x, y0 + 1, z, x, y0 + 2, z, "air")

    # 7) stair cores
    for which in ("NE", "SW"):
        stair_core(m, k, which)

def stair_core(m, k, which, penthouse=False):
    """Switchback core in a 7x7 corner square. Local u 0..6 across, w 0..6 along.
    Lane A u 0..2 rises away from hall (w 1..3), mid landing w 4..6, lane B u 4..6 rises back (w 3..2),
    arrival at w 1 on next slab, hall landing row w 0. Separator wall u 3, w 1..3."""
    y0 = yb(k)
    away = "-z" if which == "NE" else "+z"
    back = "+z" if which == "NE" else "-z"
    W = lambda u, w: core_world(u, w, which)
    # core enclosure walls (ring of the 7x7 corner square sits on corridor/outer walls already;
    # here we add the inner side walls that face the wings)
    for u in range(0, 7):
        for w in range(0, 7):
            x, z = W(u, w)
            for dy in range(1, H):
                m.set(x, y0 + dy, z, "air")
    # slab of this storey inside core: holes for the flight below (from storey k-1)
    if k >= 1:
        for u in range(0, 7):
            for w in range(0, 7):
                x, z = W(u, w)
                hole = (u <= 2 and w >= 1) or (u >= 4 and w >= 3) or (u == 3 and w >= 4)
                if hole: m.set(x, y0, z, "air")
        # top step of previous storey's lane B sits in this slab
        for u in (4, 5, 6):
            x, z = W(u, 2); m.set(x, y0, z, "stone_brick_stairs", {"weirdo_direction": ASC[back]})
    # separator wall
    for w in (1, 2, 3):
        x, z = W(3, w)
        for dy in range(1, H): m.set(x, y0 + dy, z, "stone_bricks")
    # lane A: 3 steps up at w=1,2,3 heights +1..+3
    for i, w in enumerate((1, 2, 3)):
        for u in (0, 1, 2):
            x, z = W(u, w); m.set(x, y0 + 1 + i, z, "stone_brick_stairs", {"weirdo_direction": ASC[away]})
    # mid landing at +3, w 4..6 across all u
    for u in range(0, 7):
        for w in (4, 5, 6):
            x, z = W(u, w); m.set(x, y0 + 3, z, "polished_andesite")
    # lane B: step at w=3 height +4 (w=2 height +5 is next slab, placed by storey k+1 / roof)
    for u in (4, 5, 6):
        x, z = W(u, 3); m.set(x, y0 + 4, z, "stone_brick_stairs", {"weirdo_direction": ASC[back]})
    # light
    x, z = W(3, 5); m.set(x, y0 + 4, z, "lantern", {"hanging": True})

def roof(m, y0):
    # parapet + garden + core penthouses
    for x in range(-R, R + 1):
        for z in range(-R, R + 1):
            inside = footprint(N - 1, x, z)
            if not inside: continue
            edge = ring(x, z) == R or (x == -CW and z <= -CW) or (z == -CW and x <= -CW) or (x == CW and z >= CW) or (z == CW and x >= CW)
            if edge: m.set(x, y0 + 1, z, "quartz_slab", {"minecraft:vertical_half": "bottom"})
    # skylight frame
    for x in range(-ATR - 1, ATR + 2):
        for z in range(-ATR - 1, ATR + 2):
            if ring(x, z) == ATR + 1: m.set(x, y0 + 1, z, "glass_pane")
    # garden beds
    for (x1, z1, x2, z2) in [(-6, 9, 6, 11), (-11, -6, -9, 6), (9, -6, 11, 6), (-6, -11, 6, -9)]:
        m.box(x1, y0 + 1, z1, x2, y0 + 1, z2, "moss_block")
        for x in range(x1, x2 + 1, 3):
            m.set(x, y0 + 2, z1 + 1, "azalea")
    # stair top step & penthouse over each core
    for which in ("NE", "SW"):
        back = "+z" if which == "NE" else "-z"
        W = lambda u, w, wh=which: core_world(u, w, wh)
        for u in range(0, 7):
            for w in range(0, 7):
                x, z = W(u, w)
                hole = (u <= 2 and w >= 1) or (u >= 4 and w >= 3) or (u == 3 and w >= 4)
                if hole: m.set(x, y0, z, "air")
                wall = u in (0, 6) or w == 6 or (w == 0)
                for dy in range(1, H):
                    if wall: m.set(x, y0 + dy, z, "white_concrete")
                    else: m.set(x, y0 + dy, z, "air")
                m.set(x, y0 + H - 1, z, "light_gray_concrete")     # penthouse roof
        for u in (4, 5, 6):
            x, z = W(u, 2); m.set(x, y0, z, "stone_brick_stairs", {"weirdo_direction": ASC[back]})
        # penthouse door onto roof (hall side, w == 0)
        x, z = W(2, 0); m.box(x, y0 + 1, z, x, y0 + 2, z, "air")
        x, z = W(1, 0); m.box(x, y0 + 1, z, x, y0 + 2, z, "air")
        x, z = W(3, 3); m.set(x, y0 + 3, z, "lantern", {"hanging": True})

def make_model():
    m = Model()
    for k in range(N + 1):
        build_storey(m, k)
    return m

# ---------------------------------------------------------------- compile & transport
def boxes(cells):
    """cells: dict (x,y,z)->key. Greedy mesh: x-runs, merge along z, then along y."""
    rows = defaultdict(list)  # (y,z,key) -> sorted xs
    for (x, y, z), key in cells.items(): rows[(y, z, key)].append(x)
    runs = []
    for (y, z, key), xs in rows.items():
        xs.sort(); a = p = xs[0]
        for x in xs[1:]:
            if x == p + 1: p = x
            else: runs.append((y, z, a, p, key)); a = p = x
        runs.append((y, z, a, p, key))
    # merge along z
    byk = defaultdict(set)
    for r in runs: byk[(r[0], r[2], r[3], r[4])].add(r[1])
    slabs = []
    for (y, a, b, key), zs in byk.items():
        zs = sorted(zs); s = q = zs[0]
        for z in zs[1:]:
            if z == q + 1: q = z
            else: slabs.append((a, b, s, q, y, key)); s = q = z
        slabs.append((a, b, s, q, y, key))
    # merge along y
    byk2 = defaultdict(set)
    for (a, b, s, q, y, key) in slabs: byk2[(a, b, s, q, key)].add(y)
    out = []
    for (a, b, s, q, key), ys in byk2.items():
        ys = sorted(ys); s0 = q0 = ys[0]
        for y in ys[1:]:
            if y == q0 + 1: q0 = y
            else: out.append((a, s0, s, b, q0, q, key)); s0 = q0 = y
        out.append((a, s0, s, b, q0, q, key))
    return out

class Conn:
    def __init__(s):
        s.s = socket.create_connection(("127.0.0.1", 8767)); s.f = s.s.makefile("rw")
    def req(s, obj):
        s.f.write((obj if isinstance(obj, str) else json.dumps(obj, separators=(",", ":"))) + "\n"); s.f.flush()
        return json.loads(s.f.readline())

def send_fill(c, bxs):
    ops, size, placed, errs = [], 0, 0, []
    def flush():
        nonlocal ops, size, placed
        if not ops: return
        r = c.req({"op": "fill", "ops": ops})
        if "result" in r: placed += r["result"]["placed"]; errs.extend(r["result"]["errors"])
        else: errs.append(r)
        ops, size = [], 0
    # air first so that later solid boxes overwrite cleared space correctly (order within storey)
    bxs = sorted(bxs, key=lambda b: (b[6][0] != "air",))
    for (x1, y1, z1, x2, y2, z2, (b, st)) in bxs:
        op = [x1, y1, z1, x2, y2, z2, b] + ([json.loads(st)] if st else [])
        n = len(json.dumps(op, separators=(",", ":")))
        if size + n > 1500: flush()
        ops.append(op); size += n
    flush()
    return placed, errs

def storey_cells(m, k):
    lo, hi = yb(k), yb(k) + H - 1
    return {p: v for p, v in m.v.items() if lo <= p[1] <= hi}

def verify(c, m, k):
    lo = yb(k); bad = []
    for y in range(lo, lo + H):
        r = c.req({"op": "scan", "from": [-R, y, -R], "to": [R, y, R]})
        res = r["result"]; pal = res["palette"]
        rows = res["layers"][0]
        for zi, row in enumerate(rows):
            x = -R
            for run in row.split(","):
                idx, _, n = run.partition("*"); n = int(n or 1)
                key = pal[int(idx)]
                for _ in range(n):
                    z = -R + zi
                    want = m.v.get((x, y, z))
                    if want:
                        got_t = key.split("{")[0]
                        if got_t != want[0]:
                            bad.append(((x, y, z), want[0], got_t))
                        elif want[1] and "weirdo_direction" in want[1]:
                            wd = json.loads(want[1])["weirdo_direction"]
                            if f'"weirdo_direction":{wd}' not in key: bad.append(((x, y, z), want, key))
                    x += 1
    return bad

GLYPH = {"air": " ", "white_concrete": "#", "glass": "~", "glass_pane": ":", "quartz_pillar": "O",
         "stone_bricks": "|", "stone_brick_stairs": "s", "polished_andesite": "=", "spruce_fence": "+",
         "light_gray_concrete": "%", "lantern": "*", "flowering_azalea": "T", "azalea": "t", "moss_block": "m",
         "quartz_slab": "-", "fern": "f", "quartz_block": "Q"}

def plan(m, k, dy):
    y = yb(k) + dy
    print(f"--- storey {k} y={y} (+{dy}) ---   north is up (-z), east is right (+x)")
    for z in range(-R, R + 1):
        print("".join(GLYPH.get(m.v.get((x, y, z), ("?",))[0], "?") if (x, y, z) in m.v else "." for x in range(-R, R + 1)))

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    ks = [int(a) for a in sys.argv[2:]] or list(range(N + 1))
    m = make_model()
    print(f"model: {len(m.v)} voxels, {sum(1 for v in m.v.values() if v[0] != 'air')} solid")
    if cmd == "plan":
        for k in ks:
            plan(m, k, 1); plan(m, k, 2)
        sys.exit()
    c = Conn()
    for k in ks:
        if cmd == "build":
            bx = boxes(storey_cells(m, k))
            placed, errs = send_fill(c, bx)
            print(f"storey {k}: {len(bx)} boxes, {placed} blocks placed, {len(errs)} errors", errs[:3])
        bad = verify(c, m, k)
        print(f"storey {k}: verify -> {len(bad)} mismatches", bad[:5])

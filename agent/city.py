#!/usr/bin/env python3
"""Procedural city builder around the downtown core. Runs forever as a service (mc-city).

Grid: road centrelines x = -44 + 64*i, z = -88 + 64*j  (roads 9 wide: 5 asphalt + 2x2 sidewalk).
Core cells (i in 0..1, j in 0..2) hold the hand-built downtown and are not replaced.
Each new cell: roads on its 4 edges (lamps, crosswalks, traffic lights), then a plot building
chosen by distance from downtown, verified by scan, recorded in city/state.json, tour updated.

  city.py run            build forever (ring by ring)
  city.py one I J [type] build a single cell now
  city.py status
"""
import json, math, os, random, subprocess, sys, time
from tower import Model, Conn, boxes, send_fill, G, ASC
import puppet, tour, interiors

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "city", "state.json")
BACKUPS = os.path.expanduser("~/mc-bds/backups")
PACE = 30            # seconds between buildings
MAX_RING = int(os.environ.get("MC_CITY_MAX_RING", "6"))   # raise to keep expanding outward
CORE = {(i, j) for i in (0, 1) for j in (0, 1, 2)}
XL = lambda i: -44 + 64 * i
ZL = lambda j: -88 + 64 * j
LEAF = {"persistent_bit": True}

def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)

# ------------------------------------------------------------------ palette probing
CANDIDATES = {
    "glass": ["light_blue_stained_glass", "cyan_stained_glass", "gray_stained_glass", "blue_stained_glass", "glass", "black_stained_glass"],
    "frame": ["white_concrete", "light_gray_concrete", "gray_concrete", "black_concrete", "quartz_block", "smooth_stone", "polished_andesite"],
    "brick": ["brick_block", "white_terracotta", "orange_terracotta", "brown_terracotta", "light_gray_terracotta", "red_nether_brick", "mud_bricks", "stone_bricks"],
    "wood": ["oak_planks", "spruce_planks", "birch_planks", "dark_oak_planks", "acacia_planks", "cherry_planks", "mangrove_planks"],
    "awning": ["red_wool", "blue_wool", "green_wool", "yellow_wool", "orange_wool", "white_wool", "purple_wool", "cyan_wool"],
    "tree": ["oak", "birch", "spruce", "cherry", "acacia", "dark_oak"],
}
FIXED = ["black_concrete", "yellow_concrete", "white_concrete", "smooth_stone", "polished_andesite", "iron_bars", "lantern",
         "verdant_froglight", "ochre_froglight", "red_concrete", "sea_lantern", "grass_block", "water", "oak_fence", "spruce_fence",
         "dark_oak_fence", "glass_pane", "iron_block", "end_rod", "lightning_rod", "stone_bricks", "gravel", "flowering_azalea",
         "poppy", "cornflower", "allium", "oxeye_daisy", "dandelion", "azure_bluet", "spruce_stairs", "oak_stairs", "stone_brick_stairs",
         "smooth_quartz", "light_gray_concrete", "gray_concrete", "white_wool", "hay_block", "barrel", "chiseled_stone_bricks", "quartz_pillar",
         "deepslate_tiles", "polished_deepslate", "moss_block", "lily_pad", "waterlily", "spruce_slab", "bookshelf", "crafting_table", "glowstone"]
PAL = {}

def probe(c):
    names = set(FIXED) | {n for v in CANDIDATES.values() for n in v}
    names |= {f"{t}_log" for t in CANDIDATES["tree"]} | {f"{t}_leaves" for t in CANDIDATES["tree"]}
    names |= {f"{w.replace('_planks', '')}_stairs" for w in CANDIDATES["wood"]}
    ok = set()
    for n in sorted(names):
        r = c.req({"op": "fill", "ops": [[0, 310, 0, 0, 310, 0, n]]})
        if not r.get("result", {}).get("errors"): ok.add(n)
    c.req({"op": "fill", "ops": [[0, 310, 0, 0, 310, 0, "air"]]})
    for k, v in CANDIDATES.items():
        PAL[k] = [n for n in v if n in ok] if k != "tree" else [t for t in v if f"{t}_log" in ok and f"{t}_leaves" in ok]
    PAL["ok"] = ok
    log("probe:", {k: len(v) for k, v in PAL.items() if k != "ok"}, "missing:", sorted(names - ok))

def has(n): return n in PAL["ok"]

# ------------------------------------------------------------------ shared helpers
def tree(m, x, z, kind, h=5):
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            for dy in range(h - 2, h + 2):
                if math.sqrt(dx * dx + dz * dz + (dy - h + 0.5) ** 2 * 1.6) <= 2.9 and not (abs(dx) == 3 and abs(dz) == 3):
                    m.set(x + dx, G + 1 + dy, z + dz, f"{kind}_leaves", LEAF)
    m.box(x, G + 1, z, x, G + h, z, f"{kind}_log")

def bench(m, x, z, face):  # face: direction the sitter looks
    back = {"+x": "-x", "-x": "+x", "+z": "-z", "-z": "+z"}[face]
    m.set(x, G + 1, z, "spruce_stairs", {"weirdo_direction": ASC[back]})

def lamp(m, x, z, h=4):
    m.box(x, G + 1, z, x, G + h, z, "dark_oak_fence"); m.set(x, G + h + 1, z, "lantern")

def pave(m, x0, z0, x1, z1, b="smooth_stone"):
    m.box(x0, G, z0, x1, G, z1, b)

# ------------------------------------------------------------------ roads
def road(m, axis, c, a, b, crossings):
    """axis 'x': road runs along x at z=c (from x=a..b). axis 'z': along z at x=c."""
    for t in range(a, b + 1):
        near = min((abs(t - cc) for cc in crossings), default=99)
        for o in range(-4, 5):
            x, z = (t, c + o) if axis == "x" else (c + o, t)
            if near <= 4:                              # intersection box
                blk = "smooth_stone" if abs(o) >= 3 and near >= 3 else "black_concrete"
            elif abs(o) <= 2:
                if 5 <= near <= 6: blk = "white_concrete" if o % 2 == 0 else "black_concrete"   # zebra crossing
                elif o == 0 and t % 6 < 3: blk = "yellow_concrete"
                else: blk = "black_concrete"
            else:
                blk = "polished_andesite" if abs(o) == 3 else "smooth_stone"
            m.set(x, G, z, blk)
        # street lamps alternate sides, not near intersections
        if near > 7 and t % 16 == 0:
            for o in (-4, 4):
                x, z = (t, c + o) if axis == "x" else (c + o, t)
                m.box(x, G + 1, z, x, G + 5, z, "iron_bars"); m.set(x, G + 6, z, "sea_lantern")
        if near > 9 and t % 64 == 32:                  # benches mid-block
            for o, f in ((-4, "+z" if axis == "x" else "+x"), (4, "-z" if axis == "x" else "-x")):
                x, z = (t + 2, c + o) if axis == "x" else (c + o, t + 2)
                bench(m, x, z, f)
    for cc in crossings:                               # traffic lights on the 4 corners
        if a <= cc <= b:
            for ox in (-4, 4):
                for ot in (-4, 4):
                    x, z = (cc + ot, c + ox) if axis == "x" else (c + ox, cc + ot)
                    m.box(x, G + 1, z, x, G + 4, z, "iron_bars")
                    m.set(x, G + 5, z, "verdant_froglight"); m.set(x, G + 6, z, "ochre_froglight"); m.set(x, G + 7, z, "red_concrete")

def cell_roads(m, i, j):
    xs = [XL(k) for k in range(-12, 14)]; zs = [ZL(k) for k in range(-12, 14)]
    edges = [("x", ZL(j), (i, j - 1)), ("x", ZL(j + 1), (i, j + 1)), ("z", XL(i), (i - 1, j)), ("z", XL(i + 1), (i + 1, j))]
    for axis, c, nb in edges:
        if (i, j) in CORE and nb in CORE: continue     # no roads through downtown
        if axis == "x": road(m, "x", c, XL(i) - 4, XL(i + 1) + 4, xs)
        else: road(m, "z", c, ZL(j) - 4, ZL(j + 1) + 4, zs)

# ------------------------------------------------------------------ plot types
def office(m, r, x0, z0, x1, z1):
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    hw = r.randint(10, 18); hd = r.randint(10, 18)
    n = r.randint(8, 22); FH = 4
    glass, frame = r.choice(PAL["glass"]), r.choice(PAL["frame"])
    pave(m, x0, z0, x1, z1)
    for (tx, tz) in [(x0 + 3, z0 + 3), (x1 - 3, z0 + 3), (x0 + 3, z1 - 3), (x1 - 3, z1 - 3)]:
        m.set(tx, G, tz, "grass_block"); tree(m, tx, tz, r.choice(PAL["tree"]), 4)
    setback = int(n * r.uniform(0.5, 0.75))
    floors = []
    for f in range(n + 1):
        y = G + FH * f
        ins = 0 if f < 2 else (2 if f < setback else 5)
        ax0, ax1, az0, az1 = cx - hw + ins, cx + hw - ins, cz - hd + ins, cz + hd - ins
        if ax1 - ax0 < 6 or az1 - az0 < 6: n = f; break
        m.box(ax0, y, az0, ax1, y, az1, "smooth_stone")
        for lx in range(ax0 + 3, ax1 - 1, 5):
            for lz in range(az0 + 3, az1 - 1, 5): m.set(lx, y, lz, "sea_lantern")
        if f == n:
            m.box(ax0, y + 1, az0, ax1, y + 1, az0, frame); m.box(ax0, y + 1, az1, ax1, y + 1, az1, frame)
            m.box(ax0, y + 1, az0, ax0, y + 1, az1, frame); m.box(ax1, y + 1, az0, ax1, y + 1, az1, frame)
            for k in range(r.randint(1, 3)):
                ux, uz = r.randint(ax0 + 2, ax1 - 5), r.randint(az0 + 2, az1 - 5)
                m.box(ux, y + 1, uz, ux + 2, y + 2, uz + 2, "iron_block")
            ah = r.randint(6, 16)
            m.box(cx, y + 1, cz, cx, y + ah, cz, "iron_bars"); m.set(cx, y + ah + 1, cz, "end_rod")
            break
        for x in range(ax0, ax1 + 1):
            for z in range(az0, az1 + 1):
                if x not in (ax0, ax1) and z not in (az0, az1): continue
                mull = (x - ax0) % 3 == 0 and (z - az0) % 3 == 0 or (x in (ax0, ax1) and z in (az0, az1)) \
                    or (z in (az0, az1) and (x - ax0) % 3 == 0) or (x in (ax0, ax1) and (z - az0) % 3 == 0)
                for dy in range(1, FH):
                    m.set(x, y + dy, z, frame if mull else glass)
        m.box(cx - 3, y + 1, cz - 3, cx + 3, y + FH - 1, cz + 3, "light_gray_concrete")       # elevator core
        floors.append((f, y, ax0, ax1, az0, az1))
    # lobby entrances on all 4 sides
    for (ex, ez, ax) in [(cx, cz - hd, "x"), (cx, cz + hd, "x"), (cx - hw, cz, "z"), (cx + hw, cz, "z")]:
        for o in (-1, 0, 1):
            x, z = (ex + o, ez) if ax == "x" else (ex, ez + o)
            for dy in (1, 2): m.v.pop((x, G + dy, z), None)
    # interiors: carve glass meeting rooms into some corners, then detect & furnish rooms floor by floor
    themes = {}
    for (f, y, ax0, ax1, az0, az1) in floors:
        if f >= 1 and ax1 - ax0 > 16 and az1 - az0 > 16:
            for (qx, qz) in r.sample([(0, 0), (1, 0), (0, 1), (1, 1)], r.randint(0, 3)):
                ex = ax0 + 8 if qx == 0 else ax1 - 8
                ez = az0 + 7 if qz == 0 else az1 - 7
                xs = range(ax0 + 1, ex + 1) if qx == 0 else range(ex, ax1)
                zs = range(az0 + 1, ez + 1) if qz == 0 else range(ez, az1)
                for x in xs:
                    for dy in (1, 2, 3): m.set(x, y + dy, ez, "glass")
                for z in zs:
                    for dy in (1, 2, 3): m.set(ex, y + dy, z, "glass")
                door = (ex, ez - 2) if qz == 0 else (ex, ez + 2)
                for dy in (1, 2): m.set(door[0], y + dy, door[1], "air")
        theme = "cafe" if f == 0 else r.choices(["open_plan", "cafe", "library", None], [6, 1, 1, 2])[0]
        plan = (lambda R, rr, t=theme: (t if R.area >= 100 else None))
        rep = interiors.furnish_storey(m, y, (ax0 - 1, az0 - 1, ax1 + 1, az1 + 1), r, plan=plan, ceil=FH)
        themes[f] = [k for k, _ in rep]
    return {"kind": "office", "height": n * FH + 2, "name": f"{frame.split('_')[0].title()} Tower"}

def apartments(m, r, x0, z0, x1, z1):
    wall, n, D = r.choice(PAL["brick"]), r.randint(4, 9), 10
    FH = 3
    shape = r.choice(["U", "L", "O"])
    wings = [(x0 + 2, z0 + 2, x1 - 2, z0 + 1 + D)]                                # north wing
    wings.append((x0 + 2, z0 + 2, x0 + 1 + D, z1 - 2))                           # west wing
    if shape in ("U", "O"): wings.append((x1 - 1 - D, z0 + 2, x1 - 2, z1 - 2))   # east wing
    if shape == "O": wings.append((x0 + 2, z1 - 1 - D, x1 - 2, z1 - 2))          # south wing
    inside = lambda x, z: any(a <= x <= c and b <= z <= d for a, b, c, d in wings)
    for x in range(x0 + 2, x1 - 1):
        for z in range(z0 + 2, z1 - 1):
            if not inside(x, z): continue
            edge = not (inside(x - 1, z) and inside(x + 1, z) and inside(x, z - 1) and inside(x, z + 1))
            for f in range(n + 1):
                y = G + FH * f
                m.set(x, y, z, "smooth_stone" if f else "polished_andesite")
                if f == n:
                    if edge: m.set(x, y + 1, z, "stone_bricks")
                    continue
                if edge:
                    win = ((x + z) % 3 == 1)
                    m.set(x, y + 1, z, wall); m.set(x, y + 2, z, "glass_pane" if win else wall)
    # balconies on the courtyard side of the north wing
    for f in range(1, n, 2):
        y = G + FH * f
        for x in range(x0 + 4 + D, x1 - 3 - (D if shape in ("U", "O") else 0), 4):
            z = z0 + 2 + D
            m.set(x, y, z, "smooth_stone"); m.set(x + 1, y, z, "smooth_stone")
            m.set(x, y + 1, z, "iron_bars"); m.set(x + 1, y + 1, z, "iron_bars")
    # entrances
    for (x, z) in [((x0 + x1) // 2, z0 + 2), (x0 + 2, (z0 + z1) // 2)]:
        for dy in (1, 2): m.v.pop((x, G + dy, z), None)
    # courtyard: grass, trees, benches, playground sand
    for x in range(x0 + 1, x1):
        for z in range(z0 + 1, z1):
            if not inside(x, z): m.set(x, G, z, "grass_block")
    cxm, czm = (x0 + 2 + D + x1) // 2, (z0 + 2 + D + z1) // 2
    for k in range(4):
        tx, tz = r.randint(x0 + D + 5, x1 - D - 3 if shape != "L" else x1 - 4), r.randint(z0 + D + 5, z1 - 4 - (D if shape == "O" else 0))
        tree(m, tx, tz, r.choice(PAL["tree"]), r.randint(4, 6))
    for o in range(-3, 4, 3): bench(m, cxm + o, czm, "-z")
    return {"kind": "apartments", "height": n * FH + 2, "name": f"{shape}-Block Apartments"}

def gable_house(m, r, x0, z0, w, d, storeys, wood, roofwood):
    h = 4 * storeys
    x1, z1 = x0 + w - 1, z0 + d - 1
    log = r.choice([f"{t}_log" for t in PAL["tree"]])
    for y in range(G + 1, G + h + 1):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if x in (x0, x1) or z in (z0, z1):
                    corner = x in (x0, x1) and z in (z0, z1)
                    win = (y - G) % 4 == 2 and not corner and ((x - x0) % 3 == 1 if z in (z0, z1) else (z - z0) % 3 == 1)
                    m.set(x, y, z, log if corner else ("glass_pane" if win else wood))
    for f in range(storeys + 1): m.box(x0, G + 4 * f if f else G, z0, x1, G + 4 * f if f else G, z1, wood)
    st = f"{roofwood.replace('_planks', '')}_stairs"
    if not has(st): st = "spruce_stairs"
    # roof ridge along x: rows from z0-1 and z1+1 inward
    k = 0
    while z0 - 1 + k <= z1 + 1 - k:
        y = G + h + 1 + k
        a, b = z0 - 1 + k, z1 + 1 - k
        if a == b: m.box(x0 - 1, y, a, x1 + 1, y, a, roofwood)
        else:
            m.box(x0 - 1, y, a, x1 + 1, y, a, st, {"weirdo_direction": ASC["+z"]})
            m.box(x0 - 1, y, b, x1 + 1, y, b, st, {"weirdo_direction": ASC["-z"]})
            if b - a > 1:   # gable walls
                for x in (x0, x1): m.box(x, y, a + 1, x, y, b - 1, wood)
        k += 1
    return h + k

def houses(m, r, x0, z0, x1, z1):
    mid_x, mid_z = (x0 + x1) // 2, (z0 + z1) // 2
    for x in range(x0, x1 + 1):                                        # cross lanes
        for o in (-1, 0, 1): m.set(x, G, mid_z + o, "gravel")
    for z in range(z0, z1 + 1):
        for o in (-1, 0, 1): m.set(mid_x + o, G, z, "gravel")
    top = 0
    for qx in (0, 1):
        for qz in (0, 1):
            ax0 = x0 + 1 if qx == 0 else mid_x + 3; ax1 = mid_x - 3 if qx == 0 else x1 - 1
            az0 = z0 + 1 if qz == 0 else mid_z + 3; az1 = mid_z - 3 if qz == 0 else z1 - 1
            # two houses per quadrant
            for half in (0, 1):
                hx0 = ax0 + (0 if half == 0 else (ax1 - ax0) // 2 + 1)
                hx1 = ax0 + (ax1 - ax0) // 2 - 1 if half == 0 else ax1
                w = min(r.randint(8, 11), hx1 - hx0 - 1); d = r.randint(7, 9)
                hz = az1 - d - 1 if qz == 0 else az0 + 2
                wood, roofw = r.choice(PAL["wood"]), r.choice(PAL["wood"])
                top = max(top, gable_house(m, r, hx0 + 1, hz, w, d, r.choice([1, 1, 2]), wood, roofw))
                door_z = hz + d - 1 if qz == 0 else hz
                dx = hx0 + 1 + w // 2
                for dy in (1, 2): m.v.pop((dx, G + dy, door_z), None)
                walk = range(door_z + 1, mid_z - 1) if qz == 0 else range(mid_z + 2, door_z)
                for z in walk: m.set(dx, G, z, "gravel")
                # garden: fence front, flowers, a tree behind
                fz = mid_z - 2 if qz == 0 else mid_z + 2
                for x in range(hx0, hx1 + 1):
                    if x != dx: m.set(x, G + 1, fz, "oak_fence")
                m.set(hx0 + 2, G + 1, fz + (-1 if qz == 0 else 1), r.choice(["poppy", "cornflower", "allium", "dandelion"]))
                tz = hz - 3 if qz == 0 else hz + d + 2
                if az0 + 2 <= tz <= az1 - 2: tree(m, hx0 + 2, tz, r.choice(PAL["tree"]), 4)
    # little green with a well in the middle
    m.box(mid_x - 1, G + 1, mid_z - 1, mid_x + 1, G + 1, mid_z + 1, "stone_bricks"); m.set(mid_x, G + 1, mid_z, "water")
    for (x, z) in [(mid_x - 1, mid_z - 1), (mid_x + 1, mid_z + 1), (mid_x - 1, mid_z + 1), (mid_x + 1, mid_z - 1)]:
        m.box(x, G + 2, z, x, G + 3, z, "oak_fence")
    m.box(mid_x - 1, G + 4, mid_z - 1, mid_x + 1, G + 4, mid_z + 1, "spruce_slab", {"minecraft:vertical_half": "bottom"})
    return {"kind": "houses", "height": top, "name": "Garden Houses"}

def market(m, r, x0, z0, x1, z1):
    pave(m, x0, z0, x1, z1, "polished_andesite")
    D, H2 = 7, 8
    top = 0
    for side in range(4):
        t0, t1 = (x0 + 1, x1 - 1) if side < 2 else (z0 + 1 + D, z1 - 1 - D)
        for s0 in range(t0, t1 - 5, 7):
            wall, aw = r.choice(PAL["brick"] + PAL["frame"]), r.choice(PAL["awning"])
            for t in range(s0, s0 + 7):
                for dd in range(D):
                    if side == 0: x, z = t, z0 + 1 + dd
                    elif side == 1: x, z = t, z1 - 1 - dd
                    elif side == 2: x, z = x0 + 1 + dd, t
                    else: x, z = x1 - 1 - dd, t
                    front = dd == D - 1; sidewall = t in (s0, s0 + 6)
                    for y in range(G + 1, G + H2 + 1):
                        if front or sidewall or dd == 0:
                            if front and not sidewall and y <= G + 3:
                                m.set(x, y, z, "glass" if y > G + 2 or t % 7 != 3 else "air")
                            else: m.set(x, y, z, wall if not (front and y == G + 6 and t % 2) else "glass_pane")
                    m.set(x, G + H2, z, "smooth_stone"); m.set(x, G + 4, z, "smooth_stone")
                    if front:   # awning over the shop front
                        ax, az = (x, z + 1) if side == 0 else (x, z - 1) if side == 1 else (x + 1, z) if side == 2 else (x - 1, z)
                        m.set(ax, G + 4, az, aw)
            top = H2 + 1
    # plaza: fountain, trees, market stalls
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    for x in range(cx - 4, cx + 5):
        for z in range(cz - 4, cz + 5):
            d = math.hypot(x - cx, z - cz)
            if 3 <= d < 4: m.set(x, G + 1, z, "stone_bricks")
            elif d < 3: m.set(x, G, z, "water"); m.set(x, G + 1, z, "water")
    m.box(cx, G + 1, cz, cx, G + 3, cz, "chiseled_stone_bricks"); m.set(cx, G + 4, cz, "sea_lantern")
    for (sx, sz) in [(cx - 12, cz - 12), (cx + 10, cz - 12), (cx - 12, cz + 10), (cx + 10, cz + 10)]:
        aw = r.choice(PAL["awning"])
        for (px, pz) in [(sx, sz), (sx + 2, sz), (sx, sz + 2), (sx + 2, sz + 2)]: m.box(px, G + 1, pz, px, G + 2, pz, "oak_fence")
        m.box(sx, G + 3, sz, sx + 2, G + 3, sz + 2, aw); m.set(sx + 1, G + 1, sz + 1, r.choice(["hay_block", "barrel", "crafting_table"]))
    for (tx, tz) in [(cx - 8, cz), (cx + 8, cz), (cx, cz - 8), (cx, cz + 8)]:
        m.set(tx, G, tz, "grass_block"); tree(m, tx, tz, r.choice(PAL["tree"]), 4)
    # openings in the shop ring at mid-sides so the plaza is reachable from the street
    for (x, z) in [(cx, z0 + 1), (cx, z1 - 1), (x0 + 1, cz), (x1 - 1, cz)]:
        for o in (-1, 0, 1):
            for dd in range(D):
                for y in range(G + 1, G + 4):
                    xx, zz = (x + o, z + (dd if z == z0 + 1 else -dd)) if x == cx else (x + (dd if x == x0 + 1 else -dd), z + o)
                    m.v.pop((xx, y, zz), None)
    return {"kind": "market", "height": top, "name": "Market Square"}

def park_plot(m, r, x0, z0, x1, z1):
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1): m.set(x, G, z, "grass_block")
    R = min(x1 - x0, z1 - z0) / 2 - 6
    pcx, pcz = cx + r.randint(-6, 6), cz + r.randint(-6, 6)
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            d = math.hypot(x - cx, z - cz)
            if abs(d - R) < 1.2: m.set(x, G, z, "gravel")
            if ((x - pcx) / 9) ** 2 + ((z - pcz) / 6) ** 2 <= 1: m.set(x, G, z, "water"); m.set(x, G - 1, z, "water")
    for o in range(-int(R), int(R) + 1):      # cross paths to the loop
        for w in (-1, 0, 1):
            for (x, z) in [(cx + o, z0 + 2 + (o + int(R)) * 0) if False else (cx + w, cz + o), (cx + o, cz + w)]:
                if m.v.get((x, G, z), ("",))[0] != "water": m.set(x, G, z, "gravel")
    for x in range(x0, x1 + 1, 1):
        for z in (z0, z1):
            if abs(x - cx) > 1: m.set(x, G + 1, z, "oak_fence")
    for z in range(z0, z1 + 1):
        for x in (x0, x1):
            if abs(z - cz) > 1: m.set(x, G + 1, z, "oak_fence")
    for (cxx, czz) in [(cx, z0), (cx, z1), (x0, cz), (x1, cz)]:
        for o in (-1, 0, 1):
            x, z = (cxx + o, czz) if czz in (z0, z1) else (cxx, czz + o)
            m.set(x, G, z, "gravel")
    spots = []
    for _ in range(300):
        x, z = r.randint(x0 + 3, x1 - 3), r.randint(z0 + 3, z1 - 3)
        if m.v.get((x, G, z), ("",))[0] in ("water", "gravel"): continue
        if any(m.v.get((x + dx, G, z + dz), ("",))[0] in ("water", "gravel") for dx in (-3, 0, 3) for dz in (-3, 0, 3)): continue
        if any(math.hypot(x - a, z - b) < 7 for a, b in spots): continue
        spots.append((x, z))
        if len(spots) >= 14: break
    for (x, z) in spots: tree(m, x, z, r.choice(PAL["tree"]), r.randint(4, 7))
    # gazebo at centre
    for (px, pz) in [(cx - 2, cz - 2), (cx + 2, cz - 2), (cx - 2, cz + 2), (cx + 2, cz + 2)]: m.box(px, G + 1, pz, px, G + 3, pz, "oak_fence")
    m.box(cx - 3, G + 4, cz - 3, cx + 3, G + 4, cz + 3, "spruce_slab", {"minecraft:vertical_half": "bottom"})
    m.box(cx - 2, G, cz - 2, cx + 2, G, cz + 2, "spruce_planks"); m.set(cx, G + 3, cz, "lantern", {"hanging": True})
    for k in range(6):
        a = k * math.pi / 3
        x, z = round(cx + (R - 2) * math.cos(a)), round(cz + (R - 2) * math.sin(a))
        lamp(m, x, z)
    for k in range(10):
        x, z = r.randint(x0 + 2, x1 - 2), r.randint(z0 + 2, z1 - 2)
        if (x, G + 1, z) not in m.v and m.v.get((x, G, z), ("",))[0] == "grass_block":
            m.set(x, G + 1, z, r.choice(["poppy", "cornflower", "allium", "oxeye_daisy", "dandelion", "azure_bluet"]))
    return {"kind": "park", "height": 10, "name": "Neighbourhood Park"}

def utility(m, r, x0, z0, x1, z1):
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    pave(m, x0, z0, x1, z1, "gray_concrete")
    # parking lot (west half): bays with white lines
    for x in range(x0 + 2, cx - 2):
        for z in range(z0 + 2, z1 - 1):
            if (z - z0) % 14 in (0,): m.set(x, G, z, "white_concrete")
            if (x - x0) % 4 == 0 and (z - z0) % 14 not in (6, 7, 8): m.set(x, G, z, "white_concrete")
    # water tower (east-north)
    tx, tz = (cx + x1) // 2, (z0 + cz) // 2
    for (lx, lz) in [(tx - 4, tz - 4), (tx + 4, tz - 4), (tx - 4, tz + 4), (tx + 4, tz + 4)]:
        m.box(lx, G + 1, lz, lx, G + 18, lz, "iron_bars")
    for y in range(G + 19, G + 28):
        for x in range(tx - 6, tx + 7):
            for z in range(tz - 6, tz + 7):
                d = math.hypot(x - tx, z - tz)
                if d <= 5.5 and (d > 4.5 or y in (G + 19, G + 27)): m.set(x, y, z, "light_gray_concrete" if y % 3 else "white_concrete")
    for y in range(G + 28, G + 32):
        rr = 5.5 - (y - G - 28) * 1.5
        for x in range(tx - 6, tx + 7):
            for z in range(tz - 6, tz + 7):
                if math.hypot(x - tx, z - tz) <= rr: m.set(x, y, z, "gray_concrete")
    m.box(tx, G + 1, tz, tx, G + 18, tz, "iron_block")
    # substation (east-south): fenced yard with transformers and lightning rods
    sx0, sz0, sx1, sz1 = cx + 3, cz + 3, x1 - 3, z1 - 3
    for x in range(sx0, sx1 + 1):
        for z in range(sz0, sz1 + 1):
            if x in (sx0, sx1) or z in (sz0, sz1): m.box(x, G + 1, z, x, G + 2, z, "iron_bars")
            else: m.set(x, G, z, "gravel")
    for x in range(sx0 + 3, sx1 - 2, 5):
        for z in range(sz0 + 3, sz1 - 2, 6):
            m.box(x, G + 1, z, x + 2, G + 3, z + 2, "iron_block")
            m.box(x + 1, G + 4, z + 1, x + 1, G + 6, z + 1, "lightning_rod")
    return {"kind": "utility", "height": 32, "name": "Water Tower & Substation"}

TYPES = {"office": office, "apartments": apartments, "houses": houses, "market": market, "park": park_plot, "utility": utility}
from villa import villa                      # on request only (city.py one I J villa); choose() never picks it
TYPES["villa"] = villa

def choose(i, j, r, built):
    ring = max(abs(i - 0.5), abs(j - 1)) - 0.5      # distance in cells from downtown
    w = {"office": max(0, 6 - 2 * ring), "apartments": 4, "market": 2, "houses": 1 + 2 * ring, "park": 2, "utility": 0.8}
    kinds = [b["kind"] for b in built.values()]
    if kinds.count("utility") >= 1 + len(kinds) // 12: w["utility"] = 0
    if kinds.count("market") >= 1 + len(kinds) // 8: w["market"] = 0.3
    ks = list(w); return r.choices(ks, [w[k] for k in ks])[0]

# ------------------------------------------------------------------ driver
def load_state():
    try: return json.load(open(STATE))
    except Exception: return {"built": {}, "order": 0}

def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"; json.dump(st, open(tmp, "w"), indent=1); os.replace(tmp, STATE)

def site_tour(cx, cz, h, size):
    rad = size / 2 + 16; y = G + max(10, h * 0.7) + 4
    W = []
    for k, deg in enumerate((200, 290, 20)):
        a = math.radians(deg + (cx * 7 + cz * 3) % 90)
        W.append(tour.wp(round(cx + rad * math.cos(a), 1), round(y - k * 3, 1), round(cz + rad * math.sin(a), 1),
                         cx, G + h * 0.45, cz, 3.5))
    return W

def ensure_loaded(c, x0, z0, x1, z1):
    c.req("tickingarea remove cityplot")
    c.req(f"tickingarea add {x0} -64 {z0} {x1} 0 {z1} cityplot true")
    for _ in range(60):
        ok = True
        for (x, z) in [(x0, z0), (x1, z0), (x0, z1), (x1, z1), ((x0 + x1) // 2, (z0 + z1) // 2)]:
            r = c.req({"op": "scan", "from": [x, G, z], "to": [x, G, z]})
            if r.get("result", {}).get("unloaded", 1): ok = False
        if ok: return True
        time.sleep(1)
    return False

def backup(c):
    os.makedirs(BACKUPS, exist_ok=True)
    c.req("save hold")
    for _ in range(30):
        r = c.req("save query")
        if any("Data saved" in l or "ready" in l.lower() for l in r.get("lines", [])): break
        time.sleep(1)
    ts = time.strftime("%Y%m%d-%H%M%S")
    subprocess.run(["tar", "czf", f"{BACKUPS}/claude_build-{ts}.tgz", "-C", os.path.expanduser("~/mc-bds/server/worlds"), "claude_build"])
    c.req("save resume")
    olds = sorted(f for f in os.listdir(BACKUPS) if f.endswith(".tgz"))
    for f in olds[:-5]: os.remove(os.path.join(BACKUPS, f))
    log("backup", ts)

def build_cell(c, st, i, j, kind=None):
    key = f"{i},{j}"
    r = random.Random(f"cell{i},{j}")
    kind = kind or choose(i, j, r, st["built"])
    x0, x1, z0, z1 = XL(i) + 5, XL(i + 1) - 5, ZL(j) + 5, ZL(j + 1) - 5
    if not ensure_loaded(c, XL(i) - 8, ZL(j) - 8, XL(i + 1) + 8, ZL(j + 1) + 8):
        log("chunks not loaded for", key); return False
    m = Model()
    cell_roads(m, i, j)
    meta = TYPES[kind](m, r, x0, z0, x1, z1)
    bx = boxes(m.v)
    t0 = time.time()
    placed, errs = send_fill(c, bx)
    bad = puppet.verify(c, m, XL(i) - 4, XL(i + 1) + 4, ZL(j) - 4, ZL(j + 1) + 4)
    if bad:   # one repair pass
        fix = Model(); fix.v = {p: m.v[p] for (p, _, _) in bad}
        send_fill(c, boxes(fix.v))
        bad = puppet.verify(c, m, XL(i) - 4, XL(i + 1) + 4, ZL(j) - 4, ZL(j + 1) + 4)
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    st["order"] = st.get("order", 0) + 1
    st["built"][key] = {"kind": meta["kind"], "name": f"{meta['name']} ({i},{j})", "center": [cx, cz], "height": meta["height"],
                        "bbox": [x0, z0, x1, z1], "order": st["order"], "blocks": sum(1 for v in m.v.values() if v[0] != "air"),
                        "errors": len(errs), "mismatches": len(bad), "tour": site_tour(cx, cz, meta["height"], x1 - x0)}
    save_state(st)
    c.req("tickingarea remove cityplot")
    log(f"built {key} {meta['name']}: {st['built'][key]['blocks']} blocks, {len(bx)} boxes, {len(errs)} errs, "
        f"{len(bad)} mismatches, {time.time() - t0:.1f}s")
    n, secs, _ = tour.upload(c)
    log(f"tour updated: {n} waypoints, {secs:.0f}s loop (swaps in at end of current loop)")
    try: c.req(f'tellraw @a {{"rawtext":[{{"text":"§a[City] §fNew: {meta["name"]} at ({cx}, {cz})"}}]}}')
    except Exception: pass
    return True

def ring_cells(R):
    cells = []
    for i in range(-R, 2 + R):
        for j in range(-R, 3 + R):
            if max(i < 0 and -i or i > 1 and i - 1 or 0, j < 0 and -j or j > 2 and j - 2 or 0) == R: cells.append((i, j))
    return sorted(cells, key=lambda c: math.atan2(ZL(c[1]) + 32, XL(c[0]) + 32 - 20))

def core_links(c):
    """Connect downtown paths to the ring road (west/east promenade ends, hall boulevard north)."""
    m = Model()
    for x in range(-40, -24):
        for z in (24, 25, 26): m.set(x, G, z, "smooth_stone")
    for x in range(65, 81):
        for z in (24, 25, 26): m.set(x, G, z, "smooth_stone")
    send_fill(c, boxes(m.v))

def run():
    c = Conn(); probe(c)
    st = load_state()
    if not st.get("links"): core_links(c); st["links"] = True; save_state(st)
    for R in range(1, MAX_RING + 1):
        for (i, j) in ring_cells(R):
            if f"{i},{j}" in st["built"] or (i, j) in CORE: continue
            try:
                build_cell(c, st, i, j)
            except Exception as e:
                log("error building", (i, j), repr(e)); time.sleep(10); c = Conn()
            if st["order"] % 10 == 0: backup(c)
            time.sleep(PACE)
    log("city complete up to ring", MAX_RING);
    while True: time.sleep(3600)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "run": run()
    elif cmd == "one":
        c = Conn(); probe(c); st = load_state()
        build_cell(c, st, int(sys.argv[2]), int(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else None)
    elif cmd == "status":
        st = load_state()
        for k, v in sorted(st["built"].items(), key=lambda kv: kv[1]["order"]):
            print(v["order"], k, v["name"], v["blocks"], "blocks, mismatches", v["mismatches"])

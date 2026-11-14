#!/usr/bin/env python3
"""Park south of the Atrium Tower and Rotunda, built by puppeteering a player.
  park.py plan | build PLAYER [speed] | verify
"""
import math, random, sys
from tower import Model, G
import puppet

X1, X2, Z1, Z2 = -24, 64, 19, 58
PLAZA = (22, 40, 7.5)          # centre x, z, radius
POND = (-6, 46, 11, 6.5)       # centre x, z, rx, rz
GY = G                         # ground layer (grass)
SETUP = ["tickingarea add -26 -64 18 66 0 60 park true"]
LEAF = {"persistent_bit": True}

def inside_pond(x, z, pad=0.0):
    cx, cz, rx, rz = POND
    return ((x - cx) / (rx + pad)) ** 2 + ((z - cz) / (rz + pad)) ** 2 <= 1

def seg_dist(px, pz, a, b):
    (ax, az), (bx, bz) = a, b
    vx, vz = bx - ax, bz - az
    t = max(0, min(1, ((px - ax) * vx + (pz - az) * vz) / (vx * vx + vz * vz)))
    return math.hypot(px - (ax + t * vx), pz - (az + t * vz))

PATHS = [  # polylines (x,z), width
    ([(-22, 25), (62, 25)], 1.6),                         # promenade
    ([(0, 17), (0, 25)], 2.1),                            # tower entrance
    ([(46, 13), (46, 25)], 1.6),                          # rotunda entrance
    ([(22, 25), (22, 33)], 1.6),                          # promenade -> plaza
    ([(29, 44), (36, 50), (46, 52), (58, 50), (62, 44)], 1.1),   # east loop
    ([(15, 44), (8, 53), (-6, 55), (-18, 52), (-21, 44), (-18, 36), (-8, 33), (2, 34), (15, 37)], 1.1),  # pond loop
    ([(62, 44), (62, 25)], 1.1),
]

def on_path(x, z):
    for pts, w in PATHS:
        for a, b in zip(pts, pts[1:]):
            if seg_dist(x, z, a, b) <= w: return True
    return False

def build(m):
    rnd = random.Random(7)
    px, pz, pr = PLAZA
    # ground: paths, plaza, pond, shore
    for x in range(X1, X2 + 1):
        for z in range(Z1, Z2 + 1):
            d_plaza = math.hypot(x - px, z - pz)
            if inside_pond(x, z):
                m.set(x, GY, z, "water"); m.set(x, GY - 1, z, "water")
            elif inside_pond(x, z, 1.2):
                m.set(x, GY, z, "sand")
            elif d_plaza <= pr:
                m.set(x, GY, z, "polished_andesite" if int(d_plaza) % 3 else "stone_bricks")
            elif on_path(x, z):
                m.set(x, GY, z, "stone_bricks" if (x + z) % 7 else "mossy_stone_bricks")
    # lily pads
    for _ in range(14):
        x = rnd.randint(POND[0] - 9, POND[0] + 9); z = rnd.randint(POND[1] - 5, POND[1] + 5)
        if inside_pond(x, z, -1.5): m.set(x, GY + 1, z, "waterlily")
    # fountain: basin ring, water, central pillar + lantern
    for x in range(px - 5, px + 6):
        for z in range(pz - 5, pz + 6):
            d = math.hypot(x - px, z - pz)
            if 3.2 <= d < 4.4: m.set(x, GY + 1, z, "stone_bricks")
            elif d < 3.2:
                m.set(x, GY, z, "water"); m.set(x, GY + 1, z, "water")
    m.box(px, GY + 1, pz, px, GY + 4, pz, "chiseled_stone_bricks")
    m.set(px, GY + 5, pz, "sea_lantern")
    # plaza benches (stairs facing the fountain) on 4 sides
    for (x, z, face) in [(px - 6, pz, 0), (px + 6, pz, 1), (px, pz - 6, 2), (px, pz + 6, 3)]:
        for o in (-1, 0, 1):
            bx, bz = (x, z + o) if face in (0, 1) else (x + o, z)
            m.set(bx, GY + 1, bz, "spruce_stairs", {"weirdo_direction": face ^ 1 if face in (0, 1) else face ^ 1})
    # lamp posts along the promenade + benches
    for x in range(-20, 62, 8):
        for z in (23, 27):
            m.box(x, GY + 1, z, x, GY + 3, z, "dark_oak_fence")
            m.set(x, GY + 4, z, "lantern")
        for z, wd in ((22, 2), (28, 3)):
            if (x + 4) % 16 == 0:
                for o in (3, 4, 5): m.set(x + o, GY + 1, z, "oak_stairs", {"weirdo_direction": wd})
    # flower beds strips along promenade
    flowers = ["poppy", "cornflower", "allium", "oxeye_daisy", "dandelion", "azure_bluet"]
    for x in range(-21, 62):
        for z in (21, 29):
            if x % 8 in (1, 2, 3, 5, 6, 7) and not on_path(x, z):
                m.set(x, GY, z, "grass_block")
                m.set(x, GY + 1, z, flowers[(x // 8 + (z == 29)) % len(flowers)])
    # trees
    spots, tries = [], 0
    while len(spots) < 26 and tries < 4000:
        tries += 1
        x, z = rnd.randint(X1 + 3, X2 - 3), rnd.randint(Z1 + 12, Z2 - 3)
        if on_path(x, z) or inside_pond(x, z, 3.5) or math.hypot(x - px, z - pz) < pr + 3: continue
        if any(seg_dist(x, z, a, b) < 3.2 for pts, w in PATHS for a, b in zip(pts, pts[1:])): continue
        if any(math.hypot(x - sx, z - sz) < 7 for sx, sz, _ in spots): continue
        spots.append((x, z, rnd.choice(["oak", "oak", "birch", "cherry"])))
    for (x, z, kind) in spots:
        h = rnd.randint(4, 6)
        log, leaves = f"{kind}_log", f"{kind}_leaves"
        for dx in range(-3, 4):
            for dz in range(-3, 4):
                for dy in range(h - 2, h + 2):
                    r = math.sqrt(dx * dx + dz * dz + (dy - h + 0.5) ** 2 * 1.6)
                    if r <= 2.9 and not (abs(dx) == 3 and abs(dz) == 3):
                        m.set(x + dx, GY + 1 + dy, z + dz, leaves, LEAF)
        m.box(x, GY + 1, z, x, GY + h, z, log)
    # hedge border with gaps where paths cross
    for x in range(X1, X2 + 1):
        for z in range(Z1, Z2 + 1):
            if (x in (X1, X2) or z == Z2) and not on_path(x, z) and not inside_pond(x, z, 1.2):
                m.set(x, GY + 1, z, "oak_leaves", LEAF)
    return m

if __name__ == "__main__":
    m = build(Model())
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if cmd == "plan":
        for z in range(Z1, Z2 + 1):
            row = ""
            for x in range(X1, X2 + 1):
                top = max((y for (xx, y, zz) in [(x, yy, z) for yy in range(GY - 1, GY + 9)] if (x, y, z) in m.v), default=None)
                b = m.v[(x, top, z)][0] if top is not None else ""
                row += {"water": "~", "stone_bricks": "=", "mossy_stone_bricks": "=", "polished_andesite": "o", "sand": ".",
                        "waterlily": "@", "oak_leaves": "T", "birch_leaves": "b", "cherry_leaves": "c", "lantern": "*",
                        "sea_lantern": "F", "": " "}.get(b, "f" if b in ("poppy", "cornflower", "allium", "oxeye_daisy", "dandelion", "azure_bluet") else "#")
            print(row)
        print(len(puppet.layered_jobs(m, 20, 38)), "jobs", sum(1 for v in m.v.values() if v[0] != "air"), "blocks")
        sys.exit()
    if cmd == "build":
        player, speed = sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
        jobs = puppet.layered_jobs(m, 20, 38)
        print(len(jobs), "jobs", flush=True)
        c = puppet.run(jobs, player, speed, (20, 38), setup=["tickingarea add -26 -64 18 66 0 60 park true"])
    else:
        from tower import Conn; c = Conn()
    bad = puppet.verify(c, m, X1, X2, Z1, Z2)
    print(f"verify: {len(bad)} mismatches", bad[:8], flush=True)

#!/usr/bin/env python3
"""Furnish the Atrium Tower: lobby by hand, upper floors by room detection. Sends only changed voxels."""
import random, sys, copy
import tower, interiors as I
from tower import Model, Conn, boxes, send_fill, yb, R, ATR, corner_core
import puppet

def lobby(m, r):
    y = yb(0)
    # reception desk facing the south entrance, quartz with gold trim
    for x in range(-4, 5):
        if abs(x) <= 1: continue
        m.set(x, y + 1, 11, "smooth_quartz"); m.set(x, y + 2, 11, "smooth_quartz_slab" if False else "quartz_slab", {"minecraft:vertical_half": "bottom"})
    for x in (-4, 4): m.set(x, y + 1, 12, "smooth_quartz"); m.set(x, y + 1, 13, "smooth_quartz")
    m.set(-3, y + 2, 11, "black_stained_glass_pane"); m.set(3, y + 2, 11, "lantern")
    I.chair(m, -2, y + 1, 10, "+z", "polished_blackstone_stairs"); I.chair(m, 2, y + 1, 10, "+z", "polished_blackstone_stairs")
    for x in range(-4, 5): m.set(x, y + 4, 11, "gold_block")          # sign band over desk
    # red carpet runner from the doors to the atrium garden
    for z in range(5, 16):
        for x in (-1, 0, 1):
            if (x, y + 1, z) not in m.v or m.v[(x, y + 1, z)][0] == "air": m.set(x, y + 1, z, "red_carpet")
    # waiting lounges either side: sofas, coffee table, plants
    for sx in (-10, 7):
        for i in range(4):
            I.chair(m, sx + i, y + 1, 14, "-z", "red_nether_brick_stairs" if r.random() < 0 else "spruce_stairs")
            m.set(sx + i, y + 1, 11, "white_wool"); I.chair(m, sx + i, y + 1, 10, "+z", "spruce_stairs")
        m.set(sx + 1, y + 1, 12, "spruce_slab", {"minecraft:vertical_half": "top"}); m.set(sx + 2, y + 1, 12, "spruce_slab", {"minecraft:vertical_half": "top"})
        m.set(sx + 1, y + 2, 12, "flowering_azalea")
        for x in range(sx - 1, sx + 5):
            for z in (12, 13):
                if (x, y + 1, z) not in m.v or m.v[(x, y + 1, z)][0] == "air": m.set(x, y + 1, z, "brown_carpet")
    # planters at the base of every quartz column, hanging lanterns between
    for x in range(-8, 9, 4):
        for z in range(-8, 9, 4):
            if max(abs(x), abs(z)) != 8: continue
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                p = (x + dx, y + 1, x and z + dz or z + dz)
                if p not in m.v or m.v[p][0] == "air": m.set(x + dx, y + 1, z + dz, "moss_block"); m.set(x + dx, y + 2, z + dz, "azalea")
    for x in range(-12, 13, 6):
        for z in range(-12, 13, 6):
            if max(abs(x), abs(z)) > 4 and (x, y + 4, z) in m.v and m.v[(x, y + 4, z)][0] == "air": m.set(x, y + 4, z, "lantern", {"hanging": True})
    # art murals on the north wall flanking the core doors, directory lectern
    for x in range(-6, 7):
        if abs(x) > 1: m.set(x, y + 2, -15, I.ART[(x + 9) % len(I.ART)]); m.set(x, y + 3, -15, I.ART[(x + 4) % len(I.ART)])
    m.set(0, y + 1, 6, "lectern")
    # cafe corner (NE of lobby, west of the stair core)
    for (x, z) in [(-12, -12), (-12, -6), (-6, -12)]:
        m.set(x, y + 1, z, "oak_fence"); m.set(x, y + 2, z, "wooden_pressure_plate")
        I.chair(m, x - 1, y + 1, z, "+x", "oak_stairs"); I.chair(m, x + 1, y + 1, z, "-x", "oak_stairs")
    for x in range(-15, -9): m.set(x, y + 1, -15, "quartz_block")
    m.set(-14, y + 2, -15, "brewing_stand"); m.set(-12, y + 1, -15, "smoker"); m.set(-11, y + 1, -15, "iron_block"); m.set(-11, y + 2, -15, "iron_block")

def main(apply=True):
    base = tower.make_model()
    m = Model(); m.v = dict(base.v)
    r = random.Random(42)
    lobby(m, r)
    report = {}
    for k in range(1, tower.N):
        report[k] = I.furnish_storey(m, yb(k), (-R - 1, -R - 1, R + 1, R + 1), r, skip=lambda x, z: corner_core(x, z) is not None)
    for k, rep in report.items(): print("floor", k, rep)
    delta = {p: v for p, v in m.v.items() if base.v.get(p) != v}
    print(len(delta), "voxels changed")
    if not apply: return
    c = Conn()
    placed, errs = send_fill(c, boxes(delta))
    print("placed", placed, "errors", len(errs), errs[:4])
    d = Model(); d.v = delta
    bad = puppet.verify(c, d, -R, R, -R, R)
    print("verify:", len(bad), "mismatches", bad[:6])

if __name__ == "__main__":
    main(apply="dry" not in sys.argv)

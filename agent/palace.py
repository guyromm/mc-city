#!/usr/bin/env python3
"""Princess Palace (Nina, 11-15): an original fairytale palace (pink walls, white quartz trim, purple/magenta and
light-blue cone roofs with gold tips), built on a DOUBLE plot at the north end of the city, on downtown's axis.

  palace.py build [I J]   build on cells (I,J)+(I+1,J) (default 0,-7), roads round both, verify + repair, state, tour
  palace.py plan          ASCII plan of the ground floor

Layout (front faces south, toward downtown): a two-storey keep with a gate and a throne hall, a grand central tower
rising from the keep roof, four corner towers, two lower wings ending in round towers, small turrets, and a front
garden with a fountain, flower beds and a lantern-lined path.
"""
import math, random, sys, time
from tower import Model, Conn, boxes, send_fill, G, ASC
import city, puppet, tour

PINK, WHITE, TRIM, GOLD = "pink_concrete", "quartz_block", "smooth_quartz", "gold_block"
CONE_A, CONE_B = "magenta_concrete", "light_blue_concrete"
GLASS, LIGHT = "light_blue_stained_glass", "sea_lantern"


def disk(r):
    R = int(math.ceil(r)) + 1
    return [(dx, dz, math.hypot(dx, dz)) for dx in range(-R, R + 1) for dz in range(-R, R + 1) if math.hypot(dx, dz) <= r + 0.45]


def tower(m, cx, cz, r, y0, y1, bands=(), windows=True):
    """Round tower: pink shell, hollow inside, quartz bands, windows on 8 sides every 6 blocks, crenellated top."""
    for y in range(y0, y1 + 1):
        for dx, dz, d in disk(r):
            if d > r - 0.6:
                b = WHITE if y in bands or y == y0 else PINK
                ang = math.degrees(math.atan2(dz, dx)) % 45
                if windows and (y - y0) % 6 in (2, 3) and y < y1 - 1 and (ang < 9 or ang > 36) and y not in bands:
                    b = GLASS
                m.set(cx + dx, y, cz + dz, b)
            else:
                m.set(cx + dx, y, cz + dz, "air")
    for dx, dz, d in disk(r):                                          # floor of the top room + crenellations
        if d <= r - 0.6: m.set(cx + dx, y1, cz + dz, TRIM)
    for k, (dx, dz, d) in enumerate(sorted((p for p in disk(r + 0.6) if p[2] > r - 0.2), key=lambda p: math.atan2(p[1], p[0]))):
        if k % 2 == 0: m.set(cx + dx, y1 + 1, cz + dz, WHITE)


def cone(m, cx, cz, r, y0, h, block):
    """Pointed roof from radius r+1 at y0 to a gold tip with a light rod on top."""
    for k in range(h):
        rr = (r + 1) * (1 - k / h)
        for dx, dz, d in disk(rr):
            m.set(cx + dx, y0 + k, cz + dz, block)
    m.set(cx, y0 + h, cz, GOLD); m.set(cx, y0 + h + 1, cz, GOLD); m.set(cx, y0 + h + 2, cz, "end_rod")


def wall_block(m, x0, z0, x1, z1, y0, y1, bands, win_every, win_rows):
    """Rectangular building shell (pink, quartz base/bands, windows), hollow, crenellated."""
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            for y in range(y0, y1 + 1):
                if not edge: m.set(x, y, z, "air"); continue
                along = x - x0 if z in (z0, z1) else z - z0
                b = WHITE if (y == y0 or y in bands) else PINK
                if any(a <= y <= b2 for a, b2 in win_rows) and along % win_every in (2, 3) and 1 < along < max(x1 - x0, z1 - z0) - 1:
                    b = GLASS
                m.set(x, y, z, b)
            if edge and (x + z) % 2 == 0: m.set(x, y1 + 1, z, WHITE)    # crenellations
    m.box(x0 + 1, y1, z0 + 1, x1 - 1, y1, z1 - 1, TRIM)                 # roof


def palace(m, r, x0, z0, x1, z1):
    cx = (x0 + x1) // 2                                                # 20 on the default plot
    m.box(x0, G, z0, x1, G, z1, "grass_block")
    # ---- keep: x cx-18..cx+18, z kz0..kz1, two floors -----------------------------------------------------------
    kx0, kx1, kz0, kz1 = cx - 18, cx + 18, z0 + 11, z0 + 30
    m.box(kx0, G, kz0, kx1, G, kz1, TRIM)
    wall_block(m, kx0, kz0, kx1, kz1, G + 1, G + 22, bands=(G + 11, G + 21), win_every=5, win_rows=((G + 3, G + 7), (G + 14, G + 18)))
    m.box(kx0 + 1, G + 11, kz0 + 1, kx1 - 1, G + 11, kz1 - 1, TRIM)      # upper floor
    for x in range(kx0 + 4, kx1 - 2, 6):                                # ceiling lights, both floors
        for z in (kz0 + 5, kz1 - 5):
            m.set(x, G + 11, z, LIGHT); m.set(x, G + 22, z, LIGHT)
    # gate: an opening with a gold frame, a red carpet to the throne
    m.box(cx - 3, G + 1, kz1, cx + 3, G + 8, kz1, "air")
    for y in range(G + 1, G + 10):
        m.set(cx - 4, y, kz1, GOLD); m.set(cx + 4, y, kz1, GOLD)
    m.box(cx - 4, G + 9, kz1, cx + 4, G + 9, kz1, GOLD)
    m.box(cx - 2, G + 10, kz1, cx + 2, G + 10, kz1, GOLD); m.set(cx, G + 11, kz1, GOLD)
    m.box(cx - 2, G + 1, kz0 + 3, cx + 2, G + 1, kz1 - 1, "red_carpet")
    m.box(cx - 2, G + 1, kz0 + 1, cx + 2, G + 1, kz0 + 2, GOLD)          # throne dais
    m.box(cx - 1, G + 2, kz0 + 1, cx + 1, G + 5, kz0 + 1, GOLD)          # throne back
    m.set(cx, G + 6, kz0 + 1, "amethyst_block")
    m.set(cx, G + 2, kz0 + 2, "quartz_stairs", {"weirdo_direction": ASC["-z"], "upside_down_bit": False})   # seat
    for x in (cx - 8, cx + 8):                                          # pillars + chandeliers in the hall
        for z in (kz0 + 6, kz1 - 6):
            m.box(x, G + 1, z, x, G + 10, z, "quartz_pillar")
    m.box(cx - 1, G + 9, (kz0 + kz1) // 2 - 1, cx + 1, G + 10, (kz0 + kz1) // 2 + 1, "glowstone")
    # ---- grand central tower on the keep roof, corner towers ---------------------------------------------------
    tcz = (kz0 + kz1) // 2
    tower(m, cx, tcz, 6, G + 23, G + 46, bands=(G + 23, G + 34, G + 45))
    cone(m, cx, tcz, 6, G + 47, 20, CONE_A)
    for (tx, tz), roof in (((kx0, kz0), CONE_B), ((kx1, kz0), CONE_B), ((kx0, kz1), CONE_A), ((kx1, kz1), CONE_A)):
        tower(m, tx, tz, 4, G + 1, G + 32, bands=(G + 11, G + 22))
        cone(m, tx, tz, 4, G + 33, 13, roof)
    # ---- wings + end towers + turrets ----------------------------------------------------------------------------
    wz0, wz1 = kz0 + 4, kz1 - 4
    for wx0, wx1, ex in ((x0 + 9, kx0 - 1, x0 + 9), (kx1 + 1, x1 - 9, x1 - 9)):
        wall_block(m, wx0, wz0, wx1, wz1, G + 1, G + 14, bands=(G + 13,), win_every=4, win_rows=((G + 3, G + 7),))
        m.box(wx0 + 1, G, wz0 + 1, wx1 - 1, G, wz1 - 1, TRIM)
        for x in range(wx0 + 3, wx1 - 1, 6): m.set(x, G + 14, (wz0 + wz1) // 2, LIGHT)
        tower(m, ex, tcz, 5, G + 1, G + 28, bands=(G + 13, G + 22))
        cone(m, ex, tcz, 5, G + 29, 14, CONE_A)
        tx = (wx0 + wx1) // 2
        tower(m, tx, wz1, 2, G + 15, G + 22, bands=(), windows=False)
        cone(m, tx, wz1, 2, G + 23, 7, CONE_B)
    # ---- front garden: path, fountain, flower beds, lanterns ----------------------------------------------------
    m.box(cx - 2, G, kz1 + 1, cx + 2, G, z1, TRIM)                      # path to the south road
    fz = (kz1 + z1) // 2 + 1
    for dx, dz, d in disk(5):
        m.set(cx + dx, G, fz + dz, TRIM if d > 3.6 else "water")
        if 3.6 < d <= 5.45: m.set(cx + dx, G + 1, fz + dz, WHITE)
    for dx, dz, d in disk(3.5):
        if d <= 3.5: m.set(cx + dx, G - 1, fz + dz, "light_blue_concrete")   # basin floor under the water
    m.box(cx, G + 1, fz, cx, G + 3, fz, "quartz_pillar"); m.set(cx, G + 4, fz, GOLD); m.set(cx, G + 5, fz, "end_rod")
    flowers = ["pink_tulip", "allium", "azure_bluet"]
    for side in (-1, 1):
        for k, z in enumerate(range(kz1 + 3, z1 - 1, 2)):
            for x in range(cx + side * 8, cx + side * 30, side * 2):
                if abs(z - fz) > 6 or abs(x - cx) > 8: m.set(x, G + 1, z, flowers[(k + abs(x)) % 3])
        for z in range(kz1 + 2, z1, 5):
            m.box(cx + side * 4, G + 1, z, cx + side * 4, G + 2, z, "oak_fence"); m.set(cx + side * 4, G + 3, z, "lantern")
    for x in range(x0, x1 + 1, 3):                                      # azalea hedge along the front edge
        if abs(x - cx) > 3: m.set(x, G + 1, z1, "flowering_azalea")
    return {"kind": "palace", "name": "Princess Palace", "height": 70}


def build(i=0, j=-7):
    c = Conn(); city.probe(c)
    st = city.load_state()
    keys = [f"{i},{j}", f"{i + 1},{j}"]
    if any(k in st["built"] for k in keys): sys.exit(f"cells {keys} already built")
    X0, X1, Z0, Z1 = city.XL(i), city.XL(i + 2), city.ZL(j), city.ZL(j + 1)
    x0, x1, z0, z1 = X0 + 5, X1 - 5, Z0 + 5, Z1 - 5
    if not city.ensure_loaded(c, X0 - 8, Z0 - 8, X1 + 8, Z1 + 8): sys.exit("chunks not loaded")
    m = Model()
    city.cell_roads(m, i, j); city.cell_roads(m, i + 1, j)
    mid = city.XL(i + 1)                                               # no road between the two cells
    for p in [p for p in m.v if mid - 4 <= p[0] <= mid + 4 and z0 <= p[2] <= z1]: del m.v[p]
    meta = palace(m, random.Random("palace"), x0, z0, x1, z1)
    t0 = time.time()
    bx = boxes(m.v); placed, errs = send_fill(c, bx)
    bad = puppet.verify(c, m, X0 - 4, X1 + 4, Z0 - 4, Z1 + 4)
    if bad:
        fix = Model(); fix.v = {p: m.v[p] for (p, _, _) in bad}; send_fill(c, boxes(fix.v))
        bad = puppet.verify(c, m, X0 - 4, X1 + 4, Z0 - 4, Z1 + 4)
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    st["order"] = st.get("order", 0) + 1
    rec = {"kind": meta["kind"], "name": meta["name"], "center": [cx, cz], "height": meta["height"], "bbox": [x0, z0, x1, z1],
           "order": st["order"], "blocks": sum(1 for v in m.v.values() if v[0] != "air"), "errors": len(errs),
           "mismatches": len(bad), "tour": city.site_tour(cx, cz, 40, x1 - x0), "cells": keys}
    for k in keys: st["built"][k] = dict(rec, tour=rec["tour"] if k == keys[0] else [])
    city.save_state(st)
    c.req("tickingarea remove cityplot")
    city.log(f"built {keys} {meta['name']}: {rec['blocks']} blocks, {len(bx)} boxes, {len(errs)} errs, {len(bad)} mismatches, "
             f"{time.time() - t0:.1f}s")
    if bad[:5]: city.log("first mismatches:", bad[:5])
    n, secs, _ = tour.upload(c)
    city.log(f"tour updated: {n} waypoints, {secs:.0f}s loop")
    c.req('tellraw @a {"rawtext":[{"text":"§d[City] §fNew: Princess Palace at (' + f"{cx}, {cz}" + ') - for Nina!"}]}')


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        build(*(int(a) for a in sys.argv[2:4]))
    elif len(sys.argv) > 1 and sys.argv[1] == "plan":
        m = Model(); palace(m, None, -39, -531, 79, -481)
        y = G + 4
        for z in range(-531, -480):
            print("".join({"pink_concrete": "#", "quartz_block": "Q", "light_blue_stained_glass": "~", "gold_block": "$",
                           "air": " ", "smooth_quartz": ".", "red_carpet": "r", "quartz_pillar": "I", "water": "o",
                           "lantern": "*", "oak_fence": "|"}.get(m.v.get((x, y, z), ("air",))[0], ",") for x in range(-39, 80)).rstrip())

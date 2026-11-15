#!/usr/bin/env python3
"""Starship (Nina, 11-15): a giant original spaceship parked on a launch pad north of the Princess Palace.

  starship.py build     build it (segment by segment: load, fill, verify + repair), record its cells, tour, chat
  starship.py stats     model size only

~300 long (nose north, -z), ~200 wide with the wings, ~60 high. Wedge hull with a cyan racing stripe, glass cockpit
canopy, portholes, swept delta wings with tip fins and nav lights, a tail fin, three engines whose glowing exhausts
face the palace, landing legs on pads, a boarding ramp up to a lit inner deck, and a painted launch pad.
Too big for one tickingarea (max 100 chunks), so the build runs in 48-block z slices.
"""
import math, sys, time
from tower import Model, Conn, boxes, send_fill, G, ASC
import city, puppet, tour

CX = 20                       # downtown / palace axis
TAIL, NOSE = -556, -856       # z of the hull's tail and nose (palace's north road is at z=-536)
L = TAIL - NOSE
YC = G + 32                   # hull centre line

TOP, SIDE, BELLY, STRIPE = "white_concrete", "light_gray_concrete", "gray_concrete", "cyan_concrete"
GLASS, LIGHT, PAD, LINE = "light_blue_stained_glass", "sea_lantern", "smooth_stone", "yellow_concrete"


def prof(z):
    """(half width, half height above centre, centre y) of the hull at z; None outside the hull."""
    if not NOSE <= z <= TAIL: return None
    t = (TAIL - z) / L                                     # 0 tail .. 1 nose
    w = 58 * (1 - max(0.0, (t - 0.55) / 0.45) ** 1.6) - 6 * max(0.0, (0.06 - t) / 0.06)
    h = 18 * (1 - max(0.0, (t - 0.45) / 0.55) ** 1.4) + 2
    yc = YC + 6 * max(0.0, (t - 0.7) / 0.3) ** 2
    return max(w, 0.5), h, yc


def inside(z, x, y):
    p = prof(z)
    if not p: return False
    w, h, yc = p
    dy = y - yc
    hh = h if dy >= 0 else 0.6 * h                         # flatter belly
    return (x - CX) ** 2 / w ** 2 + dy ** 2 / hh ** 2 <= 1


def hull(m):
    for z in range(NOSE, TAIL + 1):
        w, h, yc = prof(z)
        t = (TAIL - z) / L
        for x in range(int(CX - w - 1), int(CX + w + 2)):
            for y in range(int(yc - 0.6 * h - 1), int(yc + h + 2)):
                if not inside(z, x, y): continue
                if all(inside(z + a, x + b, y + c) for a, b, c in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))):
                    continue
                dy = y - yc
                if dy > 0.5 * h and abs(x - CX) <= 3: b = STRIPE
                elif dy > 0.35 * h: b = TOP
                elif dy >= -0.15 * h: b = SIDE
                else: b = BELLY
                if 0.72 <= t <= 0.88 and dy > 0.45 * h: b = GLASS                        # cockpit canopy
                if abs(dy) <= 1.5 and dy > -1 and (TAIL - z) % 6 in (0, 1) and 0.08 < t < 0.8 and b == SIDE: b = GLASS   # portholes
                if (TAIL - z) % 30 == 0 and b in (TOP, SIDE) and 0.05 < t < 0.85: b = SIDE if b == TOP else TOP           # panel rings
                m.set(x, y, z, b)
        # inner deck with lights
        yd = int(yc - 6)
        for x in range(int(CX - w), int(CX + w + 1)):
            if inside(z, x, yd) and (x, yd, z) not in m.v:
                m.set(x, yd, z, LIGHT if (x - CX) % 8 == 0 and (TAIL - z) % 8 == 4 else SIDE)


def wings(m):
    yw = YC - 4
    for dz in range(0, 161):
        z = TAIL - 10 - dz
        reach = 58 + 42 * (1 - dz / 160)                     # delta: widest at the rear
        for s in (-1, 1):
            for off in range(40, int(reach) + 1):
                x = CX + s * off
                if inside(z, x, yw) or inside(z, x, yw + 1): continue
                m.set(x, yw + 1, z, TOP if off < reach - 1 else STRIPE)
                m.set(x, yw, z, BELLY)
    for s, nav in ((-1, "red_concrete"), (1, "lime_concrete")):   # tip fins + nav lights at the rear wingtips
        xt = CX + s * 99
        for dz in range(0, 30):
            for y in range(yw + 2, yw + 2 + int(14 * (1 - dz / 30)) + 1):
                m.set(xt, y, TAIL - 10 - dz, TOP if dz else STRIPE)
        m.set(xt + s, yw + 1, TAIL - 10, nav); m.set(xt + s, yw + 2, TAIL - 10, LIGHT); m.set(xt + s, yw + 3, TAIL - 10, "end_rod")


def tail_fin(m):
    for dz in range(0, 55):
        z = TAIL - dz
        w, h, yc = prof(z)
        top = int(yc + h)
        for y in range(top, top + int(24 * (1 - dz / 55)) + 1):
            for x in (CX, CX + 1):
                m.set(x, y, z, STRIPE if dz < 2 or y == top + int(24 * (1 - dz / 55)) else TOP)


def engines(m):
    for ex, ey in ((CX - 30, YC - 2), (CX, YC + 5), (CX + 30, YC - 2)):
        r = 9
        for z in range(TAIL - 40, TAIL + 7):
            for dx in range(-r - 1, r + 2):
                for dy in range(-r - 1, r + 2):
                    d = math.hypot(dx, dy)
                    if d > r + 0.45: continue
                    x, y = ex + dx, ey + dy
                    if z == TAIL + 6:                                          # exhaust face toward the palace
                        b = LIGHT if d <= r - 3 else ("light_blue_concrete" if d <= r - 1.5 else "iron_block")
                    elif d > r - 0.6:
                        b = "iron_block" if z >= TAIL + 3 else BELLY
                    else:
                        continue
                    m.set(x, y, z, b)
        for k in range(3):                                                     # glow trail
            m.set(ex, ey, TAIL + 7 + k, "end_rod")


def legs_ramp_pad(m):
    # launch pad: smooth stone with a yellow border and a big target ring under the ship's middle
    px0, px1, pz0, pz1 = CX - 104, CX + 104, NOSE - 6, TAIL + 14
    m.box(px0, G, pz0, px1, G, pz1, PAD)
    for x in range(px0, px1 + 1): m.set(x, G, pz0, LINE); m.set(x, G, pz1, LINE)
    for z in range(pz0, pz1 + 1): m.set(px0, G, z, LINE); m.set(px1, G, z, LINE)
    mz = (TAIL + NOSE) // 2
    for dx in range(-41, 42):
        for dz in range(-41, 42):
            if 38.5 <= math.hypot(dx, dz) <= 40.5: m.set(CX + dx, G, mz + dz, LINE)
    for lx, lz in ((CX - 36, TAIL - 50), (CX + 36, TAIL - 50), (CX - 36, TAIL - 190), (CX + 36, TAIL - 190), (CX, TAIL - 255)):
        belly = int(prof(lz)[2] - 0.6 * prof(lz)[1])
        while inside(lz, lx, belly - 1): belly -= 1
        m.box(lx - 1, G + 1, lz - 1, lx + 1, belly, lz + 1, BELLY)
        m.box(lx - 3, G, lz - 3, lx + 3, G, lz + 3, "iron_block")
        m.box(lx - 2, G + 1, lz - 2, lx + 2, G + 1, lz + 2, "iron_block")
    # boarding ramp: stairs up from the pad (south) into the deck, through the belly
    zr = TAIL - 100
    yd = int(prof(zr)[2] - 6)
    for k in range(yd - G):
        z = zr + (yd - G) - k
        y = G + 1 + k
        for x in range(CX - 3, CX + 4):
            m.set(x, y, z, "quartz_stairs", {"weirdo_direction": ASC["-z"], "upside_down_bit": False})
            for a in (1, 2, 3):
                if (x, y + a, z) in m.v and y + a > G + 4: m.set(x, y + a, z, "air")
    for x in range(CX - 3, CX + 4):
        m.set(x, G + 1, zr + (yd - G) + 1, PAD)


def make():
    m = Model()
    legs_ramp_pad(m); hull(m); wings(m); tail_fin(m); engines(m)
    legs_ramp_pad(m)            # again, so the ramp's cleared headroom wins over the hull shell
    return m


def build():
    t0 = time.time()
    m = make()
    c = Conn(); city.probe(c)
    st = city.load_state()
    cells = [(i, j) for i in range(-2, 3) for j in range(-13, -7)]
    taken = [f"{i},{j}" for i, j in cells if f"{i},{j}" in st["built"]]
    if taken: sys.exit(f"cells already built: {taken}")
    xs = [p[0] for p in m.v]; zs = [p[2] for p in m.v]
    X0, X1, Z0, Z1 = min(xs), max(xs), min(zs), max(zs)
    city.log(f"starship model: {sum(1 for v in m.v.values() if v[0] != 'air')} blocks, x {X0}..{X1}, z {Z0}..{Z1}")
    total_bad, total_errs, nbox = 0, 0, 0
    for s0 in range(Z0, Z1 + 1, 48):
        s1 = min(s0 + 47, Z1)
        seg = Model(); seg.v = {p: v for p, v in m.v.items() if s0 <= p[2] <= s1}
        if not seg.v: continue
        if not city.ensure_loaded(c, X0, s0, X1, s1): sys.exit(f"chunks not loaded for z {s0}..{s1}")
        bx = boxes(seg.v); nbox += len(bx)
        placed, errs = send_fill(c, bx)
        bad = puppet.verify(c, seg, X0, X1, s0, s1)
        if bad:
            fix = Model(); fix.v = {p: seg.v[p] for (p, _, _) in bad}; send_fill(c, boxes(fix.v))
            bad = puppet.verify(c, seg, X0, X1, s0, s1)
        total_bad += len(bad); total_errs += len(errs)
        city.log(f"  z {s0}..{s1}: {len(seg.v)} cells, {len(bx)} boxes, {len(errs)} errs, {len(bad)} mismatches"
                 + (f" e.g. {bad[:3]}" if bad else ""))
    c.req("tickingarea remove cityplot")
    cz = (TAIL + NOSE) // 2
    st["order"] = st.get("order", 0) + 1
    rec = {"kind": "starship", "name": "Starship", "center": [CX, cz], "height": 60, "bbox": [X0, Z0, X1, Z1],
           "order": st["order"], "blocks": sum(1 for v in m.v.values() if v[0] != "air"), "errors": total_errs,
           "mismatches": total_bad, "tour": city.site_tour(CX, cz, 60, 200), "cells": [f"{i},{j}" for i, j in cells]}
    for k, (i, j) in enumerate(cells): st["built"][f"{i},{j}"] = dict(rec, tour=rec["tour"] if k == 0 else [])
    city.save_state(st)
    city.log(f"built Starship: {rec['blocks']} blocks, {nbox} boxes, {total_errs} errs, {total_bad} mismatches, {time.time() - t0:.0f}s")
    n, secs, _ = tour.upload(c)
    city.log(f"tour updated: {n} waypoints, {secs:.0f}s loop")
    c.req('tellraw @a {"rawtext":[{"text":"§b[City] §fNew: a giant Starship has landed next to the Princess Palace!"}]}')


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]: build()
    elif sys.argv[1:2] == ["stats"]:
        m = make(); xs = [p[0] for p in m.v]; ys = [p[1] for p in m.v]; zs = [p[2] for p in m.v]
        print(len(m.v), "cells,", len(boxes(m.v)), "boxes, x", min(xs), max(xs), "y", min(ys), max(ys), "z", min(zs), max(zs))

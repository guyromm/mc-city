#!/usr/bin/env python3
"""Ancient Alien Citadel (Nina, 11-16): a giant original alien megastructure on a hollow mountain, north of the Starship.

  citadel.py build     build it (tile by tile: load, fill, verify + repair), relic loot, sentinels, cells, tour, chat
  citadel.py stats     model size only
  citadel.py plan      PNG top view + section through the axis (scratch dir given as argv[2], default /tmp)

Original design: a rock mountain ~470 x 590 (3x the ship's footprint) whose inside is one huge cavern. A canyon from the
ship's launch pad runs between two glowing crescent horns and a floating eye emblem into the mountain. Inside: two giant
alien guardian statues, a floating power core (purple glass sphere with orbit rings) over a beacon whose beam rises
through a well in the mountain, and four relic sites: a stepped pyramid with a dragon egg (west), an altar of eyes with
treasure chests (east), a sculk vault of ancient relics (north), a tech garden of pedestals and a crystal grove (south).
A twisted glowing spire rises from the cavern floor through the mountain (beacon at its tip), and two pylons flank it.
Live monsters: shulkers (the only hostile mob kept on Peaceful), named Ancient Sentinel.
The whole volume is a numpy grid of material ids; only rock within 2 blocks of air is placed (a hollow shell).
"""
import json, math, os, sys, time
import numpy as np
from tower import Model, Conn, boxes, send_fill, G
import city, puppet, tour

CX = 20
X0, X1, Z0, Z1 = -222, 262, -1500, -869           # bbox (z -869 meets the ship's launch pad at -868)
NY = 200                                           # y G .. G+199
NX, NZ = X1 - X0 + 1, Z1 - Z0 + 1
MCZ, AX, AZ = -1200, 235, 295                      # mountain ellipse
WZ, CAX, CAZ = -1195, 180, 235                     # cavern ellipse, centred on the core / well
SPZ = -1360                                        # spire

MATS = [None]
MID = {}


def mid(name, st=None):
    key = (name, json.dumps(st, sort_keys=True) if st else "")
    if key not in MID:
        MID[key] = len(MATS); MATS.append(key)
    return MID[key]


A = None


def put(x, y, z, m):
    if X0 <= x <= X1 and G <= y < G + NY and Z0 <= z <= Z1: A[x - X0, y - G, z - Z0] = m


def box(x1, y1, z1, x2, y2, z2, m):
    a, b = sorted((x1, x2)); c, d = sorted((y1, y2)); e, f = sorted((z1, z2))
    a, b, c, d, e, f = max(a, X0), min(b, X1), max(c, G), min(d, G + NY - 1), max(e, Z0), min(f, Z1)
    if a <= b and c <= d and e <= f: A[a - X0:b - X0 + 1, c - G:d - G + 1, e - Z0:f - Z0 + 1] = m


def hsh(x, y, z):
    return ((np.int64(x) * 73856093) ^ (np.int64(y) * 19349663) ^ (np.int64(z) * 83492791)) & 0xFFFF


def noise2(x, z, seed):
    r = np.random.RandomState(seed); s = 0
    for k in range(5):
        f = 0.012 * 1.9 ** k; a = 0.55 ** k
        p, q, t = r.uniform(0, 6.3, 3); th = r.uniform(0, 3.14)
        u = x * math.cos(th) + z * math.sin(th); v = -x * math.sin(th) + z * math.cos(th)
        s = s + a * np.sin(u * f + p) * np.cos(v * f * 1.3 + q) + 0.4 * a * np.sin((u + v) * f * 0.7 + t)
    return s / 1.6


def shift_or(D):
    E = D.copy()
    E[1:] |= D[:-1]; E[:-1] |= D[1:]
    E[:, 1:] |= D[:, :-1]; E[:, :-1] |= D[:, 1:]
    E[:, :, 1:] |= D[:, :, :-1]; E[:, :, :-1] |= D[:, :, 1:]
    return E


# ---------------------------------------------------------------------------------------------------------------------
def mountain():
    xs = np.arange(X0, X1 + 1, dtype=float); zs = np.arange(Z0, Z1 + 1, dtype=float)
    XX, ZZ = np.meshgrid(xs, zs, indexing="ij")
    r2 = ((XX - CX) / AX) ** 2 + ((ZZ - MCZ) / AZ) ** 2
    q = np.clip(1 - r2, 0, 1)
    top = np.where(r2 < 1, G + 74 * q ** 0.55 + 8 * noise2(XX, ZZ, 7) * q ** 0.3, G - 1)
    cr2 = ((XX - CX) / CAX) ** 2 + ((ZZ - WZ) / CAZ) ** 2
    cq = np.clip(1 - cr2, 0, 1)
    n2 = noise2(XX * 2.2, ZZ * 2.2, 11)
    ceil = G + 54 * cq ** 0.5 - 7 * np.clip(n2, 0, 1) ** 2
    ceil = np.minimum(ceil, top - 7)
    cav = (cr2 < 1) & (ceil >= G + 5)
    top = np.floor(top).astype(int); ceil = np.floor(ceil).astype(int)
    R = np.zeros((NX, NY, NZ), bool)
    R[:, 0, :] = True                                          # the ground, solid for the shell test
    for k in range(1, NY):
        y = G + k
        R[:, k, :] = (top >= y) & ~(cav & (y < ceil))
    # canyon/tunnel from the pad into the cavern
    for x in range(CX - 15, CX + 16):
        dx = x - CX
        k1 = int(20 + math.sqrt(225 - dx * dx))
        R[x - X0, 1:k1 + 1, (-1010) - Z0:] = False
    # the well above the core
    wm = ((XX - CX) ** 2 + (ZZ - WZ) ** 2) <= 11.5 ** 2
    R[:, 20:, :] &= ~wm[:, None, :]
    keep = R & shift_or(shift_or(~R))
    keep[:, 0, :] = False
    # materials of the kept rock
    x, k, z = np.nonzero(keep)
    wx, wy, wz = x + X0, k + G, z + Z0
    h = hsh(wx, wy, wz)
    vein = np.abs(np.sin(0.045 * wx + 0.7 * np.sin(0.03 * wy)) + np.sin(0.05 * wz + 0.4 + 0.5 * np.sin(0.04 * wx))
                  + np.sin(0.06 * wy + 0.02 * wx)) < 0.09
    inner = cav[x, z] & (wy <= ceil[x, z] + 2)
    m = np.where(k < 25, mid("deepslate"), np.where(k < 52, mid("blackstone"), mid("tuff")))
    m = np.where(h % 5 == 0, mid("cobbled_deepslate"), m)
    m = np.where(h % 7 == 0, mid("smooth_basalt"), m)
    m = np.where(inner, np.where(h % 9 == 0, mid("tuff"), mid("deepslate")), m)
    m = np.where(vein, np.where(h % 3 == 0, mid("crying_obsidian"), mid("amethyst_block")), m)
    m = np.where(inner & (h % 41 == 0), mid("pearlescent_froglight"), m)
    m = np.where(inner & (h % 53 == 0), mid("shroomlight"), m)
    m = np.where(inner & (h % 67 == 0), mid("sea_lantern"), m)
    tun = (np.abs(wx - CX) <= 18) & (wz >= -1012) & (wy <= G + 38)
    m = np.where(tun, np.where(wz % 12 == 6, mid("sea_lantern"),
                               np.where(wz % 12 == 0, mid("purpur_block"), mid("polished_blackstone_bricks"))), m)
    well = (((wx - CX) ** 2 + (wz - WZ) ** 2) <= 15 ** 2) & (wy >= G + 20)
    m = np.where(well, np.where(wy % 8 == 0, mid("sea_lantern"), mid("purpur_block")), m)
    A[x, k, z] = m.astype(np.uint8)
    # cavern floor
    fx, fz = np.nonzero(cav)
    fh = hsh(fx + X0, G, fz + Z0)
    fm = np.where(fh % 4 == 0, mid("deepslate_tiles"), mid("polished_deepslate"))
    sc = noise2((fx + X0) * 3.0, (fz + Z0) * 3.0, 5) > 0.45
    fm = np.where(sc, mid("sculk"), fm)
    fm = np.where(fh % 61 == 0, mid("ochre_froglight"), fm)
    A[fx, 0, fz] = fm.astype(np.uint8)
    return top, ceil, cav


def cone(cx, cz, y0, r, length, down, mats, h0):
    for d in range(length):
        rr = r * (1 - d / length)
        y = y0 - d if down else y0 + d
        ri = int(rr + 1)
        for dx in range(-ri, ri + 1):
            for dz in range(-ri, ri + 1):
                if dx * dx + dz * dz <= rr * rr + 0.3:
                    put(cx + dx, y, cz + dz, mats[(h0 + d + dx * 3 + dz) % len(mats)])


def spire(cx, cz, y0, height, r0, twist, door=False):
    body, stripe, band = mid("purple_concrete"), mid("sea_lantern"), mid("black_concrete")
    ridge, win = mid("purpur_block"), mid("magenta_stained_glass")
    R0 = int(r0 * 1.3) + 3
    dx, dz = np.meshgrid(np.arange(-R0, R0 + 1), np.arange(-R0, R0 + 1), indexing="ij")
    rr = np.hypot(dx, dz); th = np.arctan2(dz, dx)
    for k in range(height):
        hh = k / height; y = y0 + k
        a = r0 * (1 - hh) ** 0.9 + 1.5
        c = np.cos(3 * (th - twist * hh))
        Rt = a * (1 + 0.28 * c)
        sh = (rr <= Rt) & (rr >= Rt - 2)
        mm = np.where(c > 0.96, stripe, np.where(c > 0.7, ridge, body))
        if y % 15 == 0: mm = np.where(c > 0.96, stripe, band)
        if k % 10 in (4, 5, 6): mm = np.where(c < -0.5, win, mm)
        if door and k < 9: sh &= ~((dz > 0) & (np.abs(dx) <= 2))
        ii, jj = np.nonzero(sh)
        for i, j in zip(ii, jj): put(cx + int(dx[i, j]), y, cz + int(dz[i, j]), int(mm[i, j]))
    yt = y0 + height
    box(cx - 1, yt, cz - 1, cx + 1, yt, cz + 1, mid("iron_block"))
    put(cx, yt + 1, cz, mid("beacon")); put(cx, yt + 2, cz, mid("purple_stained_glass"))
    return yt


def horn(s):
    body, glow = mid("purple_concrete"), mid("sea_lantern")
    for i in range(700):
        t = i / 699
        xc = CX + s * (22 + 46 * math.sin(math.pi * 0.85 * t)); yc = G + 125 * t; zc = -903 - 30 * t ** 1.5
        r = 8 * (1 - t) ** 0.8 + 1.2; ri = int(r + 1)
        for a in range(-ri, ri + 1):
            for b in range(-ri, ri + 1):
                for d in range(-ri, ri + 1):
                    if a * a + b * b + d * d <= r * r:
                        front = d >= r - 1.2 and abs(a) <= 1
                        put(int(round(xc + a)), int(round(yc + b)), int(round(zc + d)), glow if front else body)


def eye():
    ring, glass, pupil = mid("purple_concrete"), mid("magenta_stained_glass"), mid("sea_lantern")
    yc = G + 48
    for x in range(CX - 14, CX + 15):
        for y in range(yc - 10, yc + 11):
            e = ((x - CX) / 13.5) ** 2 + ((y - yc) / 9.5) ** 2
            if e > 1: continue
            m = ring if e > 0.62 else (pupil if abs(x - CX) <= 1 and abs(y - yc) <= 6 else glass)
            for z in (-905, -904): put(x, y, z, m)


def statue(sx, sz):
    blk, pur, glow, eyes = mid("black_concrete"), mid("purple_concrete"), mid("sea_lantern"), mid("verdant_froglight")
    for lx in (sx - 3, sx + 3):
        box(lx - 1, G + 1, sz - 1, lx + 1, G + 12, sz + 1, blk)
        box(lx - 1, G + 1, sz + 2, lx + 1, G + 2, sz + 3, pur)           # feet
        put(lx, G + 8, sz + 1, glow)                                      # knee light
    box(sx - 4, G + 13, sz - 1, sx + 4, G + 14, sz + 1, pur)              # hips
    for k in range(10):                                                   # torso, widening up
        w = 4 + k // 3
        box(sx - w, G + 15 + k, sz - 2, sx + w, G + 15 + k, sz + 2, blk if k % 4 else pur)
    box(sx, G + 16, sz + 2, sx, G + 23, sz + 2, glow)                    # chest seam
    for s in (-1, 1):                                                     # crescent shoulder pads, arms
        box(sx + s * 8, G + 23, sz - 3, sx + s * 10, G + 26, sz + 3, pur)
        put(sx + s * 11, G + 27, sz, pur); put(sx + s * 11, G + 28, sz, pur)
        box(sx + s * 8, G + 11, sz - 1, sx + s * 9, G + 22, sz, blk)
    box(sx - 2, G + 25, sz - 2, sx + 2, G + 30, sz + 2, blk)             # long head
    box(sx - 1, G + 31, sz - 3, sx + 1, G + 33, sz, pur)                  # crest
    put(sx - 1, G + 28, sz + 2, eyes); put(sx + 1, G + 28, sz + 2, eyes)
    box(sx + 10, G + 1, sz + 1, sx + 10, G + 30, sz + 1, mid("purpur_block"))   # staff
    for y in range(G + 30, G + 37):                                       # its crescent blade
        put(sx + 10 + (1 if y in (G + 31, G + 35) else 2 if 32 <= y - G <= 34 else 0), y, sz + 1, glow)


def pyramid_egg(px, pz):
    for k in range(10):
        hs = 10 - k
        box(px - hs, G + 1 + k, pz - hs, px + hs, G + 1 + k, pz + hs, mid("purpur_block") if k % 3 else mid("purpur_pillar"))
    put(px, G + 11, pz, mid("obsidian")); put(px, G + 12, pz, mid("dragon_egg"))
    for a, b in ((-1, -1), (-1, 1), (1, -1), (1, 1)): put(px + a, G + 11, pz + b, mid("end_rod"))
    return [(px - 6, G + 6, pz + 6), (px + 6, G + 6, pz - 6)]


def altar_eyes(px, pz, chests):
    box(px - 12, G + 1, pz - 12, px + 12, G + 1, pz + 12, mid("end_stone"))
    for x in range(px - 12, px + 13):
        for z in (pz - 12, pz + 12): put(x, G + 1, z, mid("end_bricks"))
    for z in range(pz - 12, pz + 13):
        for x in (px - 12, px + 12): put(x, G + 1, z, mid("end_bricks"))
    for i in range(7):                                       # an open arc: never a portal
        a = math.pi * (0.1 + 0.8 * i / 6)
        x, z = px + int(round(8 * math.cos(a))), pz - int(round(8 * math.sin(a)))
        put(x, G + 2, z, mid("end_portal_frame", {"direction": 0, "end_portal_eye_bit": True}))
        put(x, G + 3, z, mid("end_rod"))
    put(px, G + 2, pz, mid("lodestone")); put(px, G + 3, pz, mid("conduit"))
    for dx in (-4, 4):
        put(px + dx, G + 2, pz + 4, mid("chest")); chests.append(((px + dx, G + 2, pz + 4), "chests/end_city_treasure"))
    return [(px - 9, G + 2, pz + 9), (px + 9, G + 2, pz + 9)]


def vault(px, pz, chests):
    wall, pil, roof = mid("deepslate_tiles"), mid("reinforced_deepslate"), mid("polished_deepslate")
    x0, x1, z0, z1 = px - 20, px + 20, pz - 15, pz + 15
    box(x0, G + 1, z0, x1, G + 12, z1, wall)
    box(x0 + 1, G + 1, z0 + 1, x1 - 1, G + 12, z1 - 1, mid("air"))
    box(x0, G + 13, z0, x1, G + 13, z1, roof)
    for x in (x0, x1):
        for z in (z0, z1): box(x, G + 1, z, x, G + 16, z, pil)
    box(px - 2, G + 1, z1, px + 2, G + 7, z1, mid("air"))                # doorway (south)
    box(x0 + 1, G, z0 + 1, x1 - 1, G, z1 - 1, mid("sculk"))
    for x in range(x0 + 4, x1 - 2, 6):
        for z in (z0 + 4, z1 - 4): put(x, G + 12, z, mid("sea_lantern"))
    for x in range(x0 + 3, x1 - 2, 8): put(x, G, pz, mid("sculk_catalyst"))
    put(px, G + 1, pz, pil); put(px, G + 2, pz, mid("heavy_core"))
    for (dx, b) in ((-10, "vault"), (-6, "trial_spawner"), (6, "enchanting_table"), (10, "calibrated_sculk_sensor")):
        put(px + dx, G + 1, pz - 8, roof); put(px + dx, G + 2, pz - 8, mid(b))
    for dx in (-14, -9, 9, 14):
        for dz in (-3, 5):
            put(px + dx, G + 1, pz + dz, roof); put(px + dx, G + 2, pz + dz, mid("chest"))
            chests.append(((px + dx, G + 2, pz + dz), "chests/ancient_city"))
    return [(px - 16, G + 1, pz - 11), (px + 16, G + 1, pz - 11), (px, G + 1, pz + 8)]


def tech_garden(px, pz, chests):
    relics = ["heavy_core", "conduit", "enchanting_table", "vault", "trial_spawner", "lodestone", "copper_bulb",
              "sculk_catalyst", "calibrated_sculk_sensor", "beacon", "crying_obsidian", "amethyst_block", "end_rod",
              "lodestone", "conduit"]
    i = 0
    for r in range(3):
        for c in range(5):
            x, z = px - 16 + 8 * c, pz - 8 + 8 * r
            box(x - 1, G + 1, z - 1, x + 1, G + 2, z + 1, mid("polished_blackstone_bricks"))
            put(x, G + 2, z, mid("sea_lantern"))
            put(x, G + 3, z, mid(relics[i])); i += 1
    for x in (px - 22, px + 22):
        put(x, G + 1, pz, mid("chest")); chests.append(((x, G + 1, pz), "chests/end_city_treasure"))
    return [(px - 20, G + 1, pz - 12), (px + 20, G + 1, pz + 12)]


def crystal_grove(px, pz):
    r = np.random.RandomState(3)
    for _ in range(16):
        bx, bz = px + r.randint(-22, 23), pz + r.randint(-22, 23)
        L, rad = r.randint(10, 26), r.uniform(1.5, 3.2)
        tx, tz = r.uniform(-0.45, 0.45), r.uniform(-0.45, 0.45)
        for i in range(L):
            rr = rad * (1 - 0.8 * i / L)
            cx, cy, cz = bx + tx * i, G + 1 + i, bz + tz * i
            ri = int(rr + 1)
            for a in range(-ri, ri + 1):
                for b in range(-ri, ri + 1):
                    if a * a + b * b <= rr * rr:
                        put(int(round(cx + a)), cy, int(round(cz + b)),
                            mid("budding_amethyst") if i == 0 else mid("amethyst_block") if (a + b + i) % 5 else mid("purple_stained_glass"))


def core():
    cy = G + 30
    for x in range(CX - 34, CX + 35):                                   # plaza
        for z in range(WZ - 34, WZ + 35):
            d = math.hypot(x - CX, z - WZ)
            if d <= 34: put(x, G, z, mid("crying_obsidian") if 30 <= d <= 31 else mid("purpur_block") if (x + z) % 2 else mid("end_stone"))
    box(CX - 1, G, WZ - 1, CX + 1, G, WZ + 1, mid("iron_block")); put(CX, G + 1, WZ, mid("beacon"))
    for i in range(8):                                                  # obelisks
        a = i * math.pi / 4 + math.pi / 8
        ox, oz = CX + int(round(26 * math.cos(a))), WZ + int(round(26 * math.sin(a)))
        box(ox - 1, G + 1, oz - 1, ox + 1, G + 16, oz + 1, mid("purple_concrete"))
        box(ox - 1, G + 17, oz - 1, ox + 1, G + 18, oz + 1, mid("amethyst_block")); put(ox, G + 19, oz, mid("end_rod"))
        box(ox, G + 4, oz - 1, ox, G + 14, oz + 1, mid("sea_lantern")) if i % 2 else box(ox - 1, G + 4, oz, ox + 1, G + 14, oz, mid("sea_lantern"))
    for x in range(CX - 9, CX + 10):                                    # the core: hollow purple glass sphere
        for y in range(cy - 9, cy + 10):
            for z in range(WZ - 9, WZ + 10):
                d = math.sqrt((x - CX) ** 2 + (y - cy) ** 2 + (z - WZ) ** 2)
                if 8.2 <= d <= 9.2: put(x, y, z, mid("purple_stained_glass"))
                elif abs(y - cy) <= 0 and 5.5 <= math.hypot(x - CX, z - WZ) <= 6.5: put(x, y, z, mid("sea_lantern"))
    for tilt, axis in ((0.55, "x"), (-0.55, "z")):                      # two tilted orbit rings
        for i in range(720):
            th = i * math.pi / 360
            u, v = 16 * math.cos(th), 16 * math.sin(th)
            if axis == "x": p = (u, v * math.sin(tilt), v * math.cos(tilt))
            else: p = (v * math.cos(tilt), v * math.sin(tilt), u)
            put(CX + int(round(p[0])), cy + int(round(p[1])), WZ + int(round(p[2])),
                mid("sea_lantern") if i % 40 < 3 else mid("purpur_block"))
    return [(CX - 20, G + 1, WZ - 20), (CX + 20, G + 1, WZ - 20), (CX - 20, G + 1, WZ + 20), (CX + 20, G + 1, WZ + 20)]


def paths():
    pv, lt = mid("polished_blackstone_bricks"), mid("sea_lantern")
    def strip(x1, z1, x2, z2, along_z):
        box(x1, G, z1, x2, G, z2, pv)
        if along_z:
            for z in range(min(z1, z2), max(z1, z2) + 1, 4): put((x1 + x2) // 2, G, z, lt)
        else:
            for x in range(min(x1, x2), max(x1, x2) + 1, 4): put(x, G, (z1 + z2) // 2, lt)
    box(CX - 8, G, -895, CX + 8, G, -869, pv)                           # walkway from the launch pad
    for z in range(-895, -868, 3): put(CX - 8, G, z, lt); put(CX + 8, G, z, lt)
    strip(CX - 3, -1161, CX + 3, -896, True)                            # canyon, tunnel, cavern to the core
    strip(CX - 108, WZ - 3, CX - 35, WZ + 3, False); strip(CX + 35, WZ - 3, CX + 107, WZ + 3, False)
    strip(CX - 3, -1274, CX + 3, WZ - 35, True)
    strip(CX - 58, -1092, CX - 4, -1088, False); strip(CX + 4, -1092, CX + 58, -1088, False)


def decor(cav, ceil):
    """stalagmites, stalactites and crystal clusters, away from the paths and the sites"""
    keep_out = [(CX - 40, WZ - 40, CX + 40, WZ + 40), (CX - 20, -1200, CX + 20, -869), (CX - 140, WZ - 16, CX + 140, WZ + 16),
                (CX - 135, WZ - 15, CX - 105, WZ + 15), (CX + 105, WZ - 15, CX + 135, WZ + 15), (CX - 26, -1310, CX + 26, -1160),
                (CX - 36, SPZ - 40, CX + 36, SPZ + 40), (CX - 112, -1120, CX - 48, -1060), (CX + 48, -1120, CX + 112, -1060),
                (CX - 60, -1070, CX + 60, -1050)]
    ok = lambda x, z: not any(a <= x <= c and b <= z <= d for a, b, c, d in keep_out)
    r = np.random.RandomState(9)
    mats = [mid("dripstone_block"), mid("tuff"), mid("dripstone_block"), mid("calcite")]
    n_up = n_dn = 0
    while n_up < 70 or n_dn < 160:
        x, z = CX + r.randint(-170, 171), WZ + r.randint(-225, 226)
        if not ok(x, z) or not cav[x - X0, z - Z0]: continue
        hc = ceil[x - X0, z - Z0] - G
        if hc < 12: continue
        if n_up < 70:
            cone(x, z, G + 1, r.uniform(2, 5), int(hc * r.uniform(0.2, 0.45)), False, mats, r.randint(9)); n_up += 1
        else:
            cone(x, z, G + hc, r.uniform(1.5, 4), int(hc * r.uniform(0.15, 0.4)), True, mats, r.randint(9)); n_dn += 1
    for _ in range(40):                                                 # amethyst clusters on the floor
        x, z = CX + r.randint(-160, 161), WZ + r.randint(-215, 216)
        if not ok(x, z) or not cav[x - X0, z - Z0]: continue
        for a in range(-2, 3):
            for b in range(-2, 3):
                for c in range(0, 3):
                    if a * a + b * b + c * c * 2 <= 5: put(x + a, G + 1 + c, z + b, mid("amethyst_block") if (a + b + c) % 3 else mid("budding_amethyst"))


def make():
    global A, MATS, MID
    MATS, MID = [None], {}
    A = np.zeros((NX, NY, NZ), np.uint8)
    mid("air")
    top, ceil, cav = mountain()
    decor(cav, ceil)
    paths()
    chests, sentinels = [], []
    sentinels += core()
    statue(CX - 40, -1062); statue(CX + 40, -1062)
    sentinels += pyramid_egg(CX - 120, WZ)
    sentinels += altar_eyes(CX + 120, WZ, chests)
    sentinels += vault(CX, -1290, chests)
    sentinels += tech_garden(CX + 80, -1090, chests)
    crystal_grove(CX - 80, -1090)
    for s in (-1, 1): horn(s)
    eye()
    ys = spire(CX, SPZ, G + 1, 195, 26, 2 * math.pi * 0.6, door=True)
    put(CX, G + 1, SPZ, mid("beacon")); box(CX - 1, G, SPZ - 1, CX + 1, G, SPZ + 1, mid("iron_block"))   # root beacon (no sky: a lamp)
    for s in (-1, 1): spire(CX + s * 165, -1150, G + 1, 130, 15, -s * 2 * math.pi * 0.5)
    assert len(MATS) < 256
    return chests, sentinels, ys


def model_of(x0, x1, z0, z1):
    """Model (dict) of the voxels in x0..x1, z0..z1 (world coords)"""
    a, b, c, d = max(x0, X0) - X0, min(x1, X1) - X0, max(z0, Z0) - Z0, min(z1, Z1) - Z0
    m = Model()
    if a > b or c > d: return m
    sub = A[a:b + 1, :, c:d + 1]
    i, k, j = np.nonzero(sub)
    vals = sub[i, k, j]
    for ii, kk, jj, v in zip(i.tolist(), k.tolist(), j.tolist(), vals.tolist()):
        m.v[(ii + a + X0, kk + G, jj + c + Z0)] = MATS[v]
    return m


def split(bxs, cap=32768):
    out = []
    for bx in bxs:
        x1, y1, z1, x2, y2, z2, key = bx
        vol = (x2 - x1 + 1) * (y2 - y1 + 1) * (z2 - z1 + 1)
        if vol <= cap: out.append(bx); continue
        if y2 > y1: ym = (y1 + y2) // 2; out += split([(x1, y1, z1, x2, ym, z2, key), (x1, ym + 1, z1, x2, y2, z2, key)], cap)
        elif z2 > z1: zm = (z1 + z2) // 2; out += split([(x1, y1, z1, x2, y2, zm, key), (x1, y1, zm + 1, x2, y2, z2, key)], cap)
        else: xm = (x1 + x2) // 2; out += split([(x1, y1, z1, xm, y2, z2, key), (xm + 1, y1, z1, x2, y2, z2, key)], cap)
    return out


CELLS = [(i, j) for i in range(-3, 5) for j in range(-22, -13)]


def site_tour():
    W = tour.wp
    return [W(CX + 260, G + 120, -850, CX, G + 60, -1200, 5), W(CX, G + 32, -858, CX, G + 40, -905, 4),
            W(CX, G + 15, -930, CX, G + 15, -1000, 3.5), W(CX, G + 16, -1000, CX, G + 25, WZ, 3),
            W(CX + 28, G + 22, -1110, CX + 40, G + 20, -1062, 3), W(CX + 70, G + 20, WZ + 15, CX + 120, G + 6, WZ, 3.5),
            W(CX + 30, G + 26, WZ - 45, CX, G + 30, WZ, 3.5), W(CX + 3, G + 52, WZ, CX, G + 120, SPZ, 3),
            W(CX + 3, G + 95, WZ, CX, G + 160, SPZ, 3), W(CX + 120, G + 175, -1290, CX, G + 185, SPZ, 5)]


def build():
    t0 = time.time()
    st = city.load_state()
    taken = [f"{i},{j}" for i, j in CELLS if f"{i},{j}" in st["built"]]
    if taken: sys.exit(f"cells already built: {taken}")
    chests, sentinels, ytop = make()
    nblocks = int(np.count_nonzero(A > 1))
    city.log(f"citadel model: {nblocks} blocks, {len(MATS) - 1} materials, x {X0}..{X1}, z {Z0}..{Z1}, top y {ytop + 2}, {time.time() - t0:.0f}s")
    c = Conn(); city.probe(c)
    total_bad, total_errs, nbox = 0, 0, 0
    T = 128
    for tz in range((Z0 // 16) * 16, Z1 + 1, T):
        for tx in range((X0 // 16) * 16, X1 + 1, T):
            x0, x1, z0, z1 = max(tx, X0), min(tx + T - 1, X1), max(tz, Z0), min(tz + T - 1, Z1)
            seg = model_of(x0, x1, z0, z1)
            if not seg.v: continue
            if not city.ensure_loaded(c, x0, z0, x1, z1): sys.exit(f"chunks not loaded for {x0},{z0}..{x1},{z1}")
            bx = split(boxes(seg.v)); nbox += len(bx)
            placed, errs = send_fill(c, bx)
            bad = puppet.verify(c, seg, x0, x1, z0, z1)
            if bad:
                fix = Model(); fix.v = {p: seg.v[p] for (p, _, _) in bad}; send_fill(c, split(boxes(fix.v)))
                bad = puppet.verify(c, seg, x0, x1, z0, z1)
            total_bad += len(bad); total_errs += len(errs)
            city.log(f"  tile x {x0}..{x1} z {z0}..{z1}: {len(seg.v)} cells, {len(bx)} boxes, {len(errs)} errs, {len(bad)} mismatches"
                     + (f" e.g. {bad[:3]}" if bad else "") + (f" err {errs[:2]}" if errs else ""))
    # relic loot + sentinels (each area loaded on its own)
    nl = 0
    for (x, y, z), table in chests:
        city.ensure_loaded(c, x - 2, z - 2, x + 2, z + 2)
        r = c.req(f"loot insert {x} {y} {z} loot \"{table}\"")
        ok = not any("ERROR" in l for l in r.get("lines", []))
        nl += ok
        if not ok: city.log(f"  loot {x},{y},{z}: {r.get('lines')}")
    ns = 0
    for (x, y, z) in sentinels:
        city.ensure_loaded(c, x - 2, z - 2, x + 2, z + 2)
        r = c.req(f"summon shulker {x} {y} {z} 0 0 minecraft:entity_spawned \"Ancient Sentinel\"")
        ns += any("success" in l for l in r.get("lines", []))
    c.req("tickingarea remove cityplot")
    city.log(f"  loot: {nl}/{len(chests)} chests filled, {ns}/{len(sentinels)} sentinels summoned")
    st["order"] = st.get("order", 0) + 1
    rec = {"kind": "citadel", "name": "Ancient Alien Citadel", "center": [CX, WZ], "height": ytop + 2 - G,
           "bbox": [X0, Z0, X1, Z1], "order": st["order"], "blocks": nblocks, "errors": total_errs,
           "mismatches": total_bad, "tour": site_tour(), "cells": [f"{i},{j}" for i, j in CELLS],
           "chests": nl, "sentinels": ns}
    for k, (i, j) in enumerate(CELLS): st["built"][f"{i},{j}"] = dict(rec, tour=rec["tour"] if k == 0 else [], cells=[] if k else rec["cells"])
    city.save_state(st)
    city.log(f"built Ancient Alien Citadel: {nblocks} blocks, {nbox} boxes, {total_errs} errs, {total_bad} mismatches, {time.time() - t0:.0f}s")
    n, secs, _ = tour.upload(c)
    city.log(f"tour updated: {n} waypoints, {secs:.0f}s loop")
    c.req('tellraw @a {"rawtext":[{"text":"§d[City] §fNew: an Ancient Alien Citadel has risen behind the Starship! Explore its cavern..."}]}')


def plan(out):
    from PIL import Image
    make()
    col = {}
    rng = np.random.RandomState(1)
    pal = np.zeros((256, 3), np.uint8); pal[0] = (111, 145, 68)
    for i, (n, _) in enumerate(MATS[1:], 1):
        pal[i] = {"purple_concrete": (110, 40, 160), "sea_lantern": (200, 240, 240), "purpur_block": (170, 120, 170),
                  "deepslate": (70, 70, 75), "blackstone": (40, 35, 40), "tuff": (110, 110, 100), "amethyst_block": (150, 100, 200),
                  "polished_blackstone_bricks": (50, 45, 55), "black_concrete": (15, 15, 20), "sculk": (10, 40, 50)}.get(n, tuple(rng.randint(60, 220, 3)))
    nz = A != 0
    topk = np.where(nz.any(1), NY - 1 - np.argmax(nz[:, ::-1, :], axis=1), 0)
    img = pal[np.take_along_axis(A, topk[:, None, :], 1)[:, 0, :]]
    shade = (0.55 + 0.45 * topk / NY)[..., None]
    Image.fromarray((img * shade).astype(np.uint8).transpose(1, 0, 2)).save(f"{out}/citadel_top.png")
    sec = A[CX - X0, :, :]                                   # y x z section along the axis
    Image.fromarray(pal[sec][::-1]).resize((NZ * 2, NY * 2), Image.NEAREST).save(f"{out}/citadel_section.png")
    secx = A[:, 30, :]                                       # horizontal slice at G+30
    Image.fromarray(pal[secx].transpose(1, 0, 2)).save(f"{out}/citadel_slice30.png")
    print("written", out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]: build()
    elif sys.argv[1:2] == ["plan"]: plan(sys.argv[2] if len(sys.argv) > 2 else "/tmp")
    elif sys.argv[1:2] == ["stats"]:
        t = time.time(); ch, se, yt = make()
        print(int(np.count_nonzero(A > 1)), "blocks,", len(MATS) - 1, "materials,", len(ch), "chests,", len(se), "sentinels, top", yt + 2, f"{time.time() - t:.0f}s")
        m = model_of(-96, 31, -1280, -1153); print("sample tile", len(m.v), "cells", len(split(boxes(m.v))), "boxes")

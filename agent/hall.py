#!/usr/bin/env python3
"""Concert Hall north of the Atrium Tower and Rotunda (direct build via fastbuild.py hall)."""
import math
from tower import G, ASC

X1, X2, Z1, Z2 = 4, 46, -66, -26       # exterior walls
XC = 25
CEIL = G + 20                          # ceiling slab
BAL = G + 8                            # balcony slab level
SETUP = ["tickingarea add 0 -64 -70 50 0 -22 hall true"]

def build(m):
    up = lambda d: {"weirdo_direction": ASC[d]}
    # clear volume & foundation
    m.box(X1, G + 1, Z1, X2, CEIL + 8, Z2, "air")
    m.box(X1, G, Z1, X2, G, Z2, "polished_andesite")
    m.box(X1 + 1, G, Z1 + 1, X2 - 1, G, -35, "red_wool")                 # auditorium floor
    # exterior walls
    for x in range(X1, X2 + 1):
        for z in range(Z1, Z2 + 1):
            if x not in (X1, X2) and z not in (Z1, Z2): continue
            for y in range(G + 1, CEIL + 1):
                b = "brick_block"
                if (x in (X1, X2) and (z - Z1) % 6 == 0) or (z in (Z1, Z2) and (x - X1) % 6 == 0) or (x in (X1, X2) and z in (Z1, Z2)):
                    b = "quartz_pillar"
                elif x in (X1, X2) and Z1 + 2 <= z <= -36 and G + 10 <= y <= G + 17 and (z - Z1) % 6 in (2, 3, 4):
                    b = "glass" if y < G + 17 or (z - Z1) % 6 == 3 else "brick_block"   # arched windows
                elif y in (G + 9, CEIL):
                    b = "smooth_quartz"                                          # string courses
                m.set(x, y, z, b)
    # south facade: glass curtain over the foyer, entrance doors, canopy
    for x in range(14, 37):
        for y in range(G + 1, G + 13):
            if (x - X1) % 6: m.set(x, y, Z2, "glass")
    m.box(23, G + 1, Z2, 27, G + 3, Z2, "air")
    m.box(20, G + 5, Z2 - 0, 30, G + 5, Z2 + 3, "smooth_quartz")
    for x in (20, 30): m.box(x, G + 1, Z2 + 3, x, G + 4, Z2 + 3, "quartz_pillar")
    # ceiling with lights
    for x in range(X1 + 1, X2):
        for z in range(Z1 + 1, Z2):
            m.set(x, CEIL, z, "sea_lantern" if (x - XC) % 6 == 0 and (z % 6 == 0) else "smooth_quartz")
    # vaulted roof (deepslate tiles) over ceiling, gables filled with brick + rose window on south
    hw = (X2 - X1) / 2 + 0.5
    hgt = lambda x: int(round(7 * math.sqrt(max(0, 1 - ((x - XC) / hw) ** 2))))
    for x in range(X1 - 1, X2 + 2):
        h = hgt(x); lo = min(hgt(x - 1), hgt(x + 1), h)
        for z in range(Z1 - 1, Z2 + 2):
            for y in range(CEIL + 1 + lo, CEIL + 2 + h):
                m.set(x, y, z, "deepslate_tiles")
        for z in (Z1, Z2):
            for y in range(CEIL + 1, CEIL + 1 + lo):
                r = math.hypot(x - XC, y - (CEIL + 3))
                m.set(x, y, z, "glass" if (z == Z2 and r < 2.6) else "brick_block")
    # foyer / auditorium dividing wall with doors
    for x in range(X1 + 1, X2):
        for y in range(G + 1, CEIL):
            m.set(x, y, -34, "dark_oak_planks" if y < G + 9 else "quartz_block")
    for x0 in (16, 33): m.box(x0, G + 1, -34, x0 + 1, G + 3, -34, "air")
    m.box(24, G + 1, -34, 26, G + 3, -34, "air")
    for x0 in (6, 42): m.box(x0, G + 9, -34, x0 + 2, G + 10, -34, "air")
    # grand stairs in the foyer up to balcony level (7 steps, ascending north)
    for x0 in (6, 42):
        for i in range(7):
            m.box(x0, G + 1 + i, -27 - i, x0 + 2, G + 1 + i, -27 - i, "stone_brick_stairs", up("-z"))
            if i: m.box(x0, G + 1, -27 - i, x0 + 2, G + i, -27 - i, "stone_bricks")
        m.box(x0, BAL, -34, x0 + 2, BAL, -34, "stone_bricks")
    # foyer chandelier and benches
    chandelier(m, XC, -30, CEIL - 1, 5)
    # stage + proscenium
    m.box(X1 + 1, G + 1, Z1 + 1, X2 - 1, G + 3, -55, "spruce_planks")
    m.box(X1 + 1, G + 1, -55, X2 - 1, G + 2, -55, "dark_oak_planks")
    for x in range(X1 + 1, X2):
        for y in range(G + 1, CEIL):
            if 12 <= x <= 38 and y <= G + 14: continue
            m.set(x, y, -56, "quartz_block" if not (12 <= x <= 38) or y > G + 15 else "gold_block")
    for i, x in enumerate(range(13, 38, 2)):                               # organ pipes on back wall
        h = 7 + int(5 * math.sin(i / 12 * math.pi))
        m.box(x, G + 4, Z1 + 1, x, G + 4 + h, Z1 + 1, "iron_block")
        m.set(x, G + 5 + h, Z1 + 1, "gold_block")
    for k in range(14):                                                    # orchestra (note blocks)
        a = math.pi * (k + 0.5) / 14
        x, z = round(XC + 9 * math.cos(a)), round(-58 - 5 * math.sin(a) * -1) - 3
        m.set(x, G + 4, z, "noteblock")
    m.set(XC, G + 4, -57, "jukebox")
    # raked main-floor seating (rows of 2 z, rise 1 block every 2 rows), aisles at x 16-17 / 33-34
    for z in range(-53, -34):
        r = (z + 53) // 2; h = r // 2
        for x in range(X1 + 1, X2):
            if h: m.box(x, G + 1, z, x, G + h, z, "dark_oak_planks")
            if 10 <= x <= 40 and x not in (16, 17, 33, 34, 24, 25, 26) and (z + 53) % 2 == 0 and z <= -37:
                m.set(x, G + 1 + h, z, "crimson_stairs", up("+z"))
    # horseshoe balcony: back z -40..-35, side galleries x 5-8 / 42-45 from z -54
    m.box(X1 + 1, BAL, -40, X2 - 1, BAL, -35, "dark_oak_planks")
    m.box(X1 + 1, BAL, -54, 8, BAL, -41, "dark_oak_planks")
    m.box(42, BAL, -54, X2 - 1, BAL, -41, "dark_oak_planks")
    for x in range(9, 42): m.set(x, BAL + 1, -41, "glass_pane")
    for z in range(-54, -40): m.set(9, BAL + 1, z, "glass_pane"); m.set(41, BAL + 1, z, "glass_pane")
    m.set(9, BAL + 1, -41, "glass_pane"); m.set(41, BAL + 1, -41, "glass_pane")
    for z in (-40, -38, -36):
        for x in range(10, 41):
            if x not in (24, 25, 26): m.set(x, BAL + 1 + (z + 40) // 2, z, "crimson_stairs", up("+z"))
        if z > -40: m.box(10, BAL + 1, z, 40, BAL + (z + 40) // 2, z, "dark_oak_planks")
    # chandeliers over the auditorium
    for z in (-50, -44):
        chandelier(m, XC, z, CEIL - 1, 4)
    # boulevard south to the park, between tower and rotunda
    m.box(24, G, Z2 + 1, 26, G, 18, "stone_bricks")
    for z in range(Z2 + 4, 18, 8):
        for x in (23, 27):
            m.box(x, G + 1, z, x, G + 3, z, "dark_oak_fence"); m.set(x, G + 4, z, "lantern")
    return m

def chandelier(m, x, z, ytop, drop):
    m.box(x, ytop - drop + 1, z, x, ytop, z, "dark_oak_fence")
    y = ytop - drop
    m.set(x, y, z, "sea_lantern")
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        m.set(x + dx, y, z + dz, "glowstone"); m.set(x + 2 * dx, y - 1, z + 2 * dz, "lantern")

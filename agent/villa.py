#!/usr/bin/env python3
"""Modern villa (guy's photo, 11-15): a white two-storey house whose upper storey cantilevers over the ground floor,
a continuous glass band upstairs, floor-to-ceiling sliding glass on the living side, a thin dark roof plane above the
white roof slab, a dark wood deck, and a tiled pool with white coping.

As a city plot type: `city.py one I J villa` (roads, scan-verify + repair, state.json, tour, chat announcement).
  villa.py plan        ASCII plans of the model (ground floor, upper floor, roof) centred in a dummy plot

Orientation: the front (glass, deck, pool) faces south (+z). The entrance is on the east side, from a path to the
plot's east edge. Storeys: ground slab G, ground walls G+1..G+4, upper slab G+5, upper walls G+6..G+9, roof G+10,
dark roof plane G+11.
"""
import sys
from tower import Model, G, ASC

WALL, FLOOR, ROOF = "white_concrete", "smooth_quartz", "smooth_quartz"
GLASS, BAND, MULL = "light_gray_stained_glass", "tinted_glass", "gray_concrete"
DARK, DECK, TILE, COPING = "polished_deepslate", "dark_oak_planks", "dark_prismarine", "smooth_quartz"
LIGHT = "sea_lantern"


def villa(m, r, x0, z0, x1, z1):
    ox, oz = x0 + 12, z0 + 12                  # NW corner of the ground floor
    W, D = 22, 12                              # ground floor: x ox..ox+21, z oz..oz+11
    gx1, gz1 = ox + W - 1, oz + D - 1
    # ---- ground floor -------------------------------------------------------------------------------------
    m.box(ox, G, oz, gx1, G, gz1, FLOOR)
    m.box(ox, G + 1, oz, gx1, G + 4, gz1, WALL)                     # shell, hollowed below
    m.box(ox + 1, G + 1, oz + 1, gx1 - 1, G + 4, gz1 - 1, "air")
    # living side (west 10 columns): floor-to-ceiling sliding glass on the front and the west end
    for x in range(ox, ox + 10):
        m.box(x, G + 1, gz1, x, G + 4, gz1, MULL if (x - ox) % 3 == 0 else GLASS)
    for z in range(oz + 2, gz1):
        m.box(ox, G + 1, z, ox, G + 4, z, MULL if (z - oz) % 3 == 2 else GLASS)
    # punched windows on the rest of the front, the back and the east side
    for wx in (ox + 12, ox + 16):
        m.box(wx, G + 2, gz1, wx + 1, G + 3, gz1, GLASS)
    for wx in (ox + 3, ox + 8, ox + 13, ox + 18):
        m.box(wx, G + 2, oz, wx + 1, G + 3, oz, GLASS)
    m.box(gx1, G + 2, oz + 2, gx1, G + 3, oz + 3, GLASS)
    # entrance: a recessed door on the east side, with a canopy and a path to the plot edge
    dz = oz + 8
    m.set(gx1, G + 1, dz, "dark_oak_door", {"direction": 0, "upper_block_bit": False, "door_hinge_bit": False, "open_bit": False})
    m.set(gx1, G + 2, dz, "dark_oak_door", {"direction": 0, "upper_block_bit": True, "door_hinge_bit": False, "open_bit": False})
    m.box(gx1 + 1, G + 4, dz - 2, gx1 + 3, G + 4, dz + 2, ROOF)        # canopy
    m.box(gx1 + 1, G, dz - 1, x1, G, dz + 1, COPING)                  # path to the east road
    # ---- upper floor: cantilevers 3 west, 2 east, 2 south, 1 north --------------------------------------------
    ux0, ux1, uz0, uz1 = ox - 3, gx1 + 2, oz - 1, gz1 + 2
    m.box(ux0, G + 5, uz0, ux1, G + 5, uz1, FLOOR)
    m.box(ux0, G + 6, uz0, ux1, G + 9, uz1, WALL)
    m.box(ux0 + 1, G + 6, uz0 + 1, ux1 - 1, G + 9, uz1 - 1, "air")
    # front + west: a solid white band at the bottom, a glass ribbon above with mullions every 4
    for x in range(ux0, ux1 + 1):
        m.box(x, G + 7, uz1, x, G + 9, uz1, MULL if (x - ux0) % 4 == 0 else BAND)
    for z in range(uz0 + 1, uz1):
        m.box(ux0, G + 7, z, ux0, G + 9, z, MULL if (z - uz0) % 4 == 0 else BAND)
    for wx in range(ux0 + 3, ux1 - 2, 5):                            # back: tall windows
        m.box(wx, G + 7, uz0, wx + 1, G + 9, uz0, GLASS)
    m.box(ux1, G + 7, uz0 + 3, ux1, G + 9, uz0 + 5, GLASS)            # east window
    # ---- roof: white slab with an overhang, a thin dark plane floating above its back two thirds --------------
    m.box(ux0 - 1, G + 10, uz0 - 1, ux1 + 1, G + 10, uz1 + 1, ROOF)
    m.box(ux0 - 2, G + 11, uz0 - 2, ux1 + 2, G + 11, uz0 + 9, DARK)
    # ---- interior: lights, a straight stair to the upper floor, a little furniture ------------------------------
    for x in range(ox + 3, gx1, 5):
        for z in (oz + 3, oz + 8):
            m.set(x, G + 5, z, LIGHT)                                 # ground-floor ceiling lights
    for x in range(ux0 + 3, ux1, 5):
        for z in (uz0 + 3, uz0 + 9):
            m.set(x, G + 10, z, LIGHT)                                # upper ceiling lights
    sx, sz = ox + 12, oz + 1                                          # stair along the back wall, ascending east
    m.box(sx, G + 5, sz, sx + 3, G + 5, sz + 1, "air")                # stairwell
    for k in range(4):
        if k: m.box(sx + k, G + 1, sz, sx + k, G + k, sz + 1, FLOOR)   # solid under each step
        for z in (sz, sz + 1):
            m.set(sx + k, G + 1 + k, z, "quartz_stairs", {"weirdo_direction": ASC["+x"], "upside_down_bit": False})
    m.box(sx, G + 6, sz + 2, sx + 3, G + 6, sz + 2, "glass_pane")     # railing round the stairwell upstairs
    m.set(sx - 1, G + 6, sz, "glass_pane"); m.set(sx - 1, G + 6, sz + 1, "glass_pane")
    # living room behind the glass: sofa, coffee table, plant, bookshelf
    m.box(ox + 2, G + 1, oz + 5, ox + 2, G + 1, oz + 8, "white_wool")
    m.box(ox + 4, G + 1, oz + 6, ox + 5, G + 1, oz + 7, "dark_oak_slab")
    m.set(ox + 1, G + 1, gz1 - 1, "flowering_azalea")
    m.box(ox + 1, G + 1, oz + 1, ox + 4, G + 3, oz + 1, "bookshelf")
    m.box(ox + 1, G + 6, uz0 + 1, ox + 1, G + 6, uz0 + 2, "light_gray_wool")   # upstairs: a lounge corner
    # ---- outside: deck in front of the living side, terrace, pool, garden wall, bushes ------------------------
    m.box(ox - 6, G, gz1 + 1, ox + 10, G, gz1 + 9, DECK)              # deck (under the cantilever and beyond)
    m.box(ox - 6, G, oz, ox - 1, G, gz1, DECK)                        # wraps round the west end
    px0, pz0, px1, pz1 = ox + 11, gz1 + 4, ox + 30, gz1 + 14          # pool water (inclusive)
    m.box(ox + 11, G, gz1 + 1, px1 + 1, G, pz0 - 1, COPING)           # terrace between house and pool
    m.box(px0 - 1, G - 3, pz0 - 1, px1 + 1, G - 1, pz1 + 1, TILE)     # tiled basin
    m.box(px0, G - 2, pz0, px1, G, pz1, "water")
    for x in range(px0 - 1, px1 + 2):                                 # white coping round the water
        m.set(x, G, pz0 - 1, COPING); m.set(x, G, pz1 + 1, COPING)
    for z in range(pz0 - 1, pz1 + 2):
        m.set(px0 - 1, G, z, COPING); m.set(px1 + 1, G, z, COPING)
    for x in range(px0 + 2, px1, 6):                                  # pool lights in the floor
        m.set(x, G - 3, (pz0 + pz1) // 2, LIGHT)
    m.box(x0, G + 1, z0, x1, G + 2, z0, WALL)                         # low white garden wall at the back
    m.box(x1, G + 1, z0, x1, G + 2, dz - 2, WALL)                     # and along the east side up to the path
    for (bx, bz) in ((ox - 5, oz - 4), (ox + 6, oz - 4), (gx1 + 4, oz - 4), (ox - 8, gz1 + 6),
                     (gx1 + 5, dz + 4), (px1 + 4, pz0 + 1), (px1 + 4, pz1 - 1)):
        m.set(bx, G + 1, bz, "flowering_azalea")
    return {"kind": "villa", "name": "Villa", "height": 12}


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "plan":
    m = Model(); x0, z0 = 0, 0
    villa(m, None, x0, z0, x0 + 54, z0 + 54)
    G2 = {"white_concrete": "#", "smooth_quartz": ".", "light_gray_stained_glass": "~", "tinted_glass": "=", "gray_concrete": "|",
          "polished_deepslate": "D", "dark_oak_planks": "w", "dark_prismarine": "t", "water": "o", "sea_lantern": "*",
          "dark_oak_door": "d", "quartz_stairs": "s", "glass_pane": ":", "white_wool": "S", "dark_oak_slab": "_",
          "flowering_azalea": "f", "bookshelf": "B", "light_gray_wool": "S", "air": " "}
    for y, label in ((G, "ground slab"), (G + 2, "ground floor"), (G + 7, "upper floor"), (G + 11, "roof")):
        print(f"--- {label} (y={y}) ---")
        for z in range(z0, z0 + 55):
            print("".join(G2.get(m.v.get((x, y, z), ("air",))[0], "?") for x in range(x0, x0 + 55)).rstrip())

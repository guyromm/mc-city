"""Room detection + furnishing for building models (tower.Model).

furnish_storey(m, y, bounds, rnd, skip=None, lobby=False)
  y      = slab y of the storey (floor); furniture goes at y+1.., segmentation at y+3
  bounds = (x0, z0, x1, z1) search window
"""
import math
from collections import deque
from tower import ASC

ART = ["magenta_glazed_terracotta", "light_blue_glazed_terracotta", "orange_glazed_terracotta", "lime_glazed_terracotta",
       "cyan_glazed_terracotta", "purple_glazed_terracotta", "yellow_glazed_terracotta", "blue_glazed_terracotta", "red_glazed_terracotta"]
CARPET = ["gray_carpet", "light_gray_carpet", "blue_carpet", "green_carpet", "red_carpet", "brown_carpet", "cyan_carpet"]
TOP = {"minecraft:vertical_half": "top"}
OPP = {"+x": "-x", "-x": "+x", "+z": "-z", "-z": "+z"}
DIRS = {"+x": (1, 0), "-x": (-1, 0), "+z": (0, 1), "-z": (0, -1)}

def solid(m, p):
    v = m.v.get(p); return bool(v) and v[0] != "air"

def free(m, p): return not solid(m, p)

def chair(m, x, y, z, faces, mat="dark_oak_stairs"):
    m.set(x, y, z, mat, {"weirdo_direction": ASC[OPP[faces]]})

def regions(m, y, bounds, skip=None, ceil=5):
    x0, z0, x1, z1 = bounds; ys = y + 3
    inside = lambda x, z: solid(m, (x, y, z)) and free(m, (x, ys, z)) and free(m, (x, y + 1, z)) and solid(m, (x, y + ceil, z))
    seen, out = set(), []
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if (x, z) in seen: continue
            if not inside(x, z): continue
            q, cells, edge = deque([(x, z)]), set(), False
            seen.add((x, z))
            while q:
                cx, cz = q.popleft(); cells.add((cx, cz))
                if cx in (x0, x1) or cz in (z0, z1): edge = True
                for dx, dz in DIRS.values():
                    n = (cx + dx, cz + dz)
                    if n in seen or not (x0 <= n[0] <= x1 and z0 <= n[1] <= z1): continue
                    if inside(*n):
                        seen.add(n); q.append(n)
            if edge or (skip and any(skip(cx, cz) for cx, cz in cells)): continue
            out.append(cells)
    return out

class Room:
    def __init__(s, m, y, cells):
        s.m, s.y, s.cells = m, y, cells
        xs = [c[0] for c in cells]; zs = [c[1] for c in cells]
        s.x0, s.x1, s.z0, s.z1 = min(xs), max(xs), min(zs), max(zs)
        s.area = len(cells)
        s.fill = s.area / ((s.x1 - s.x0 + 1) * (s.z1 - s.z0 + 1))
        s.wall = {c for c in cells if any((c[0] + dx, c[1] + dz) not in cells for dx, dz in DIRS.values())}
        s.clear = set()
        for (cx, cz) in cells:          # door cells: neighbour outside region but passable at y+1/y+2
            for dx, dz in DIRS.values():
                n = (cx + dx, cz + dz)
                if n not in cells and free(m, (n[0], y + 1, n[1])) and free(m, (n[0], y + 2, n[1])):
                    for ax in (-1, 0, 1):
                        for az in (-1, 0, 1): s.clear.add((cx + ax, cz + az))
        s.used = set(s.clear)
    def ok(s, cells): return all(c in s.cells and c not in s.used for c in cells)
    def take(s, cells): s.used |= set(cells)
    def wall_dir(s, c):
        """direction from cell c towards an adjacent solid wall (for wall-hugging furniture)."""
        for d, (dx, dz) in DIRS.items():
            if (c[0] + dx, c[1] + dz) not in s.cells and solid(s.m, (c[0] + dx, s.y + 2, c[1] + dz)): return d
        return None
    def put(s, c, dy, b, st=None): s.m.set(c[0], s.y + dy, c[1], b, st)

# ------------------------------------------------------------------ furniture pieces
def desk(R, c, face, r, monitor=True):
    R.put(c, 1, "dark_oak_slab", TOP)
    if monitor and r.random() < 0.85: R.put(c, 2, "black_stained_glass_pane")
    elif r.random() < 0.5: R.put(c, 2, "lantern")

def plant(R, c, r):
    R.put(c, 1, r.choice(["moss_block", "podzol", "moss_block"]))
    R.put(c, 2, r.choice(["flowering_azalea", "azalea", "flowering_azalea"]))

def carpet(R, r, colour=None, cells=None):
    col = colour or r.choice(CARPET)
    for c in (cells or R.cells):
        if (c[0], R.y + 1, c[1]) not in R.m.v or R.m.v[(c[0], R.y + 1, c[1])][0] == "air": R.put(c, 1, col)

def pendants(R, step=4):
    for (x, z) in R.cells:
        if (x - R.x0) % step == step // 2 and (z - R.z0) % step == step // 2 and (x, z) not in R.wall:
            if free(R.m, (x, R.y + 3, z)) and solid(R.m, (x, R.y + 4, z)): R.put((x, z), 3, "lantern", {"hanging": True})

def art_wall(R, r):
    """replace a stretch of an interior partition with a glazed-terracotta mural."""
    cand = []
    for c in R.wall:
        d = R.wall_dir(c)
        if not d: continue
        wx, wz = c[0] + DIRS[d][0], c[1] + DIRS[d][1]
        if R.m.v.get((wx, R.y + 2, wz), ("",))[0] in ("white_concrete", "dark_oak_planks", "quartz_block", "light_gray_concrete"):
            cand.append((wx, wz))
    if not cand: return
    a = r.choice(ART); b = r.choice(ART)
    for i, (wx, wz) in enumerate(sorted(cand)[: r.randint(3, 6)]):
        for dy in (2, 3):
            if R.m.v.get((wx, R.y + dy, wz), ("",))[0] != "air": R.m.set(wx, R.y + dy, wz, a if (i + dy) % 2 else b)

def wall_run(R, blocks, n, r, height=1):
    """place up to n wall-hugging items from `blocks` cycling."""
    k = 0
    for c in sorted(R.wall - R.used):
        if k >= n: break
        if not R.wall_dir(c): continue
        for dy in range(1, height + 1): R.put(c, dy, blocks[k % len(blocks)])
        R.take([c]); k += 1

# ------------------------------------------------------------------ room types
def open_plan(R, r):
    carpet(R, r, r.choice(["gray_carpet", "light_gray_carpet", "blue_carpet"]))
    mat = r.choice(["dark_oak_stairs", "spruce_stairs", "birch_stairs"])
    for x in range(R.x0 + 2, R.x1 - 3, 6):
        for z in range(R.z0 + 2, R.z1 - 1, 4):
            pod = [(x + i, z + j) for i in range(4) for j in range(2)]
            if not R.ok(pod): continue
            R.take([(x + i, z + j) for i in range(-1, 5) for j in range(-1, 3)])
            for j in range(2):
                chair(R.m, x, R.y + 1, z + j, "+x", mat); desk(R, (x + 1, z + j), "-x", r)
                desk(R, (x + 2, z + j), "+x", r); chair(R.m, x + 3, R.y + 1, z + j, "-x", mat)
            if R.ok([(x + 5, z)]): plant(R, (x + 5, z), r); R.take([(x + 5, z)])
    wall_run(R, ["bookshelf", "barrel", "bookshelf", "moss_block"], 6, r)
    pendants(R)

def meeting(R, r):
    carpet(R, r, r.choice(["red_carpet", "blue_carpet", "cyan_carpet"]))
    w, d = R.x1 - R.x0 + 1, R.z1 - R.z0 + 1
    long_x = w >= d
    cx, cz = (R.x0 + R.x1) // 2, (R.z0 + R.z1) // 2
    L = max(2, (w if long_x else d) - 6)
    cells = [(cx - L // 2 + i, cz) if long_x else (cx, cz - L // 2 + i) for i in range(L)]
    if R.ok(cells):
        for c in cells:
            R.put(c, 1, "spruce_slab", TOP)
            for s in (-1, 1):
                sc = (c[0], c[1] + s) if long_x else (c[0] + s, c[1])
                if R.ok([sc]): chair(R.m, sc[0], R.y + 1, sc[1], ("-z" if s > 0 else "+z") if long_x else ("-x" if s > 0 else "+x"), "polished_blackstone_stairs" if r.random() < 0.5 else "dark_oak_stairs"); R.take([sc])
        R.take(cells)
        R.put(cells[len(cells) // 2], 2, "lantern")
    # presentation screen on the far short wall
    end = (R.x1 if long_x else cx, cz if long_x else R.z1)
    for o in (-1, 0, 1):
        wx, wz = (end[0] + 1, end[1] + o) if long_x else (end[0] + o, end[1] + 1)
        for dy in (2, 3):
            if solid(R.m, (wx, R.y + dy, wz)): R.m.set(wx, R.y + dy, wz, "white_wool" if dy == 3 or o else "black_concrete")
    plant(R, (R.x0, R.z0), r) if R.ok([(R.x0, R.z0)]) else None
    pendants(R, 3)

def break_room(R, r):
    carpet(R, r, "white_carpet" if r.random() < 0.5 else "light_gray_carpet")
    kit = ["iron_block", "smoker", "quartz_block", "cauldron", "quartz_block", "brewing_stand", "barrel", "quartz_block"]
    k = 0
    for c in sorted(R.wall - R.used):
        if k >= len(kit): break
        if not R.wall_dir(c): continue
        b = kit[k]
        if b == "brewing_stand": R.put(c, 1, "quartz_block"); R.put(c, 2, "brewing_stand")
        elif b == "iron_block": R.put(c, 1, "iron_block"); R.put(c, 2, "iron_block")        # fridge
        else: R.put(c, 1, b)
        R.take([c]); k += 1
    for x in range(R.x0 + 2, R.x1 - 1, 4):
        for z in range(R.z0 + 2, R.z1 - 1, 4):
            cells = [(x, z), (x + 1, z), (x, z + 1), (x + 1, z + 1)]
            if not R.ok([(x - 1, z), (x + 2, z)] + cells): continue
            R.put((x, z), 1, "oak_fence"); R.put((x, z), 2, "wooden_pressure_plate")         # bistro table
            for (sx, sz, f) in [(x - 1, z, "+x"), (x + 1, z, "-x")]:
                chair(R.m, sx, R.y + 1, sz, f, "oak_stairs")
            R.take([(x - 1, z), (x, z), (x + 1, z)])
    # vending machine
    for c in sorted(R.wall - R.used):
        if R.wall_dir(c): R.put(c, 1, "red_concrete"); R.put(c, 2, "glass"); R.take([c]); break
    pendants(R, 3)

def library(R, r):
    carpet(R, r, r.choice(["green_carpet", "brown_carpet", "red_carpet"]))
    for c in sorted(R.wall - R.used):
        if R.wall_dir(c) and (c[0] + c[1]) % 5:
            R.put(c, 1, "bookshelf"); R.put(c, 2, "bookshelf"); R.take([c])
    cx, cz = (R.x0 + R.x1) // 2, (R.z0 + R.z1) // 2
    for (dx, dz, f) in [(-2, 0, "+x"), (2, 0, "-x"), (0, -2, "+z"), (0, 2, "-z")]:   # armchairs around a rug
        c = (cx + dx, cz + dz)
        if R.ok([c]): chair(R.m, c[0], R.y + 1, c[1], f, "spruce_stairs"); R.take([c])
    if R.ok([(cx, cz)]): R.put((cx, cz), 1, "lectern" if r.random() < 0.4 else "spruce_slab", None if r.random() < 0.4 else TOP); R.take([(cx, cz)])
    for c in [(R.x0 + 1, R.z0 + 1), (R.x1 - 1, R.z1 - 1)]:
        if R.ok([c]): plant(R, c, r); R.take([c])
    pendants(R, 3)

def exec_office(R, r):
    carpet(R, r, "red_carpet")
    cx, cz = (R.x0 + R.x1) // 2, (R.z0 + R.z1) // 2
    big = [(cx - 1, cz), (cx, cz), (cx + 1, cz)]
    if R.ok(big + [(cx, cz + 1)]):
        for c in big: R.put(c, 1, "dark_oak_planks")
        R.put((cx - 1, cz), 2, "lantern"); R.put((cx + 1, cz), 2, "black_stained_glass_pane")
        chair(R.m, cx, R.y + 1, cz - 1, "+z", "polished_blackstone_stairs")
        chair(R.m, cx - 1, R.y + 1, cz + 2, "-z", "dark_oak_stairs"); chair(R.m, cx + 1, R.y + 1, cz + 2, "-z", "dark_oak_stairs")
        R.take(big + [(cx, cz - 1), (cx - 1, cz + 2), (cx + 1, cz + 2)])
    wall_run(R, ["bookshelf", "bookshelf", "jukebox", "bookshelf", "gold_block"], 8, r, 2)
    for c in [(R.x0, R.z0), (R.x1, R.z0), (R.x0, R.z1), (R.x1, R.z1)]:
        if R.ok([c]): plant(R, c, r); R.take([c])
    art_wall(R, r); pendants(R, 3)

def private_office(R, r):
    carpet(R, r)
    for c in sorted(R.wall - R.used):
        d = R.wall_dir(c)
        if not d: continue
        inward = OPP[d]; s = (c[0] + DIRS[inward][0], c[1] + DIRS[inward][1])
        if R.ok([c, s]):
            desk(R, c, d, r); chair(R.m, s[0], R.y + 1, s[1], d, "spruce_stairs"); R.take([c, s]); break
    wall_run(R, ["bookshelf", "barrel"], 3, r, 2)
    for c in sorted(R.cells - R.used, reverse=True):
        if c in R.wall: plant(R, c, r); R.take([c]); break
    pendants(R, 3)

def server_room(R, r):
    for c in R.cells: R.m.set(c[0], R.y, c[1], "blue_ice") if solid(R.m, (c[0], R.y, c[1])) else None
    for x in range(R.x0 + 1, R.x1, 2):
        col = [(x, z) for z in range(R.z0 + 1, R.z1)]
        for c in col:
            if c in R.cells and c not in R.used:
                R.put(c, 1, "black_concrete"); R.put(c, 2, "observer" if (c[1] % 2) else "black_concrete")
                R.put(c, 3, "verdant_froglight" if (c[0] + c[1]) % 3 == 0 else "black_concrete"); R.take([c])
    pendants(R, 4)

def closet(R, r):
    wall_run(R, ["barrel", "chest", "barrel", "bookshelf"], 6, r, 1)

def corridor(R, r):
    for c in R.cells:
        if c not in R.wall: R.put(c, 1, "gray_carpet")
    k = 0
    for c in sorted(R.wall - R.used):
        k += 1
        if k % 7 == 0 and R.wall_dir(c) and R.ok([c]): plant(R, c, r); R.take([c])
        elif k % 11 == 0 and R.wall_dir(c) and R.ok([c]):
            chair(R.m, c[0], R.y + 1, c[1], OPP[R.wall_dir(c)], "spruce_stairs"); R.take([c])
    art_wall(R, r); pendants(R, 5)

def cafe(R, r):
    for c in R.cells:
        if (c[0] + c[1]) % 2 == 0: R.put(c, 1, "brown_carpet")
    break_room(R, r)

def furnish_storey(m, y, bounds, r, skip=None, plan=None, ceil=5):
    """plan: optional fn(room, rnd) -> room-type name; default picks by size/shape."""
    rooms = [Room(m, y, cells) for cells in regions(m, y, bounds, skip, ceil)]
    report = []; n_server = 0
    for R in rooms:
        kind = plan(R, r) if plan else None
        if not kind:
            if R.fill < 0.7 and R.area > 60: kind = "corridor"
            elif R.area < 14: kind = "closet"
            elif R.area < 45:
                kind = r.choices(["private_office", "server_room", "closet"], [7, 0 if n_server else 2, 1])[0]
            elif R.area < 100: kind = r.choice(["meeting", "break_room", "library", "exec_office", "meeting", "private_office"])
            else: kind = r.choice(["open_plan", "open_plan", "cafe", "library"])
        if kind == "server_room": n_server += 1
        KINDS[kind](R, r); report.append((kind, R.area))
    return report

KINDS = {"open_plan": open_plan, "meeting": meeting, "break_room": break_room, "library": library, "exec_office": exec_office,
         "private_office": private_office, "server_room": server_room, "closet": closet, "corridor": corridor, "cafe": cafe}

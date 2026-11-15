#!/usr/bin/env python3
"""Tour route = downtown core segments + concert hall + city sites (city/state.json) + finale.
   tour.py upload | start PLAYER | stop | status"""
import json, math, os, sys
from tower import Conn, G

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "city", "state.json")
S = lambda k: G + 5 * k + 1.0          # feet height standing on tower/rotunda storey k
CX, CZ = 46, 0
MAX_SITES = 14                          # newest city sites included each loop (+ overview)

def wp(x, y, z, lx, ly, lz, secs): return [x, y, z, lx, ly, lz, int(secs * 20)]

def core():
    W = []
    W += [wp(70, -15, 85, 22, -50, 15, 4), wp(40, -35, 65, 22, -58, 38, 5), wp(22, -52, 52, 22, -57, 40, 4)]
    W += [wp(14, -57.5, 40, 22, -57, 40, 3), wp(4, -58, 50, -6, -61, 46, 3), wp(-12, -58.5, 47, -20, -59, 40, 3)]
    W += [wp(-14, -57, 27, 0, -57, 25, 3), wp(0, -58.5, 30, 0, -58, 10, 3), wp(0, -58.6, 15, 0, -58, 0, 2.5),
          wp(0.5, -58.6, 7.5, 0, -55, 0, 3)]
    for i, k in enumerate((0.5, 1.5, 2.5, 3.5)):
        a = math.radians(90 * i + 45)
        W.append(wp(math.cos(a) * 1.5, G + 5 * k + 3, math.sin(a) * 1.5, math.cos(a + 2) * 6, G + 5 * k + 3, math.sin(a + 2) * 6, 2.5))
    W += [wp(0, S(2) + 1.5, 0, 6, S(2) + 1, 0, 2.5)]
    for (x, z, lx, lz) in [(6, -6, 6, 6), (6, 6, -6, 6), (-6, 6, -6, -6), (-6, -6, 6, -6), (6, -6, 6, 1)]:
        W.append(wp(x + 0.5, S(2) + 0.1, z + 0.5, lx, S(2) + 1.5, lz, 2.5))
    W += [wp(6.5, S(2) + 0.1, 1.0, 16, S(2) + 1.5, 1, 1.5), wp(12, S(2) + 0.1, 1.0, 34, S(2) + 1.5, 1, 1.5),
          wp(25, S(2) + 0.1, 1.0, 46, S(2) + 1.5, 1, 2.5), wp(36, S(2) + 0.1, 1.0, 46, S(2) + 1.5, -6, 2)]
    for deg in (200, 250, 300, 350):
        a = math.radians(deg)
        W.append(wp(CX + 0.5 + 10 * math.cos(a), S(2) + 0.2, CZ + 0.5 + 10 * math.sin(a), CX, S(2) + 1.5, CZ, 2))
    for i in range(20, 60, 2):
        a = math.radians(18 * i + 9); a2 = math.radians(18 * i + 70)
        surf = G + 1 + i // 2 + 0.5
        W.append(wp(CX + 0.5 + 3.6 * math.cos(a), surf + 0.1, CZ + 0.5 + 3.6 * math.sin(a),
                    CX + 0.5 + 3.6 * math.cos(a2), surf + 1.6, CZ + 0.5 + 3.6 * math.sin(a2), 0.6))
    W += [wp(CX + 4, G + 31.5, CZ + 4, CX, G + 42, CZ, 2), wp(CX, G + 38, CZ, CX + 8, G + 33, CZ - 6, 3),
          wp(CX - 6, G + 50, CZ - 6, 25, G + 20, -30, 3)]
    return W

def hall():
    return [wp(25, -57, -8, 25, -56, -26, 3), wp(25, -59.9, -22, 25, -58, -34, 2), wp(25, -59.9, -29, 25, -55, -40, 2),
            wp(25, -59.9, -34, 25, -57, -50, 1.5), wp(25, -55.8, -37, 25, -55, -50, 1.5), wp(25, -56.5, -46, 25, -54, -60, 2),
            wp(25, -50, -54, 25, -50, -64, 2.5), wp(25, -45, -48, 25, -55, -40, 3), wp(25, -50.8, -38, 25, -52, -55, 2.5),
            wp(36, -50, -30, 36, -48, -10, 2), wp(36, -40, -12, 25, -45, -45, 2)]

def city():
    try: st = json.load(open(STATE))
    except Exception: return []
    sites = sorted(st.get("built", {}).values(), key=lambda s: s.get("order", 0))[-MAX_SITES:]
    if not sites: return []
    # visit newest sites in angular order around downtown so the flight path stays smooth
    sites.sort(key=lambda s: math.atan2(s["center"][1] - 0, s["center"][0] - 20))
    W = []
    for s in sites: W += s["tour"]
    # overview orbit sized to the whole city
    ext = max(max(abs(s["center"][0] - 20), abs(s["center"][1])) for s in st["built"].values()) + 60
    for deg in range(0, 360, 60):
        a = math.radians(deg)
        W.append(wp(20 + ext * math.cos(a), G + 90, ext * math.sin(a), 20, G, 0, 5))
    return W

def finale():
    return [wp(0, -28, -10, 0, -36, 8, 3), wp(0, -32, 10, 0, -40, 30, 3), wp(20, -40, 40, 40, -45, 60, 3)]

def route():
    return core() + hall() + city() + finale()

def upload(c=None):
    c = c or Conn()
    W = [[round(v, 2) for v in w[:6]] + [w[6]] for w in route()]
    chunks, cur = [], []
    for w in W:
        if len(json.dumps(cur + [w], separators=(",", ":"))) > 1700: chunks.append(cur); cur = []
        cur.append(w)
    chunks.append(cur)
    for j, ch in enumerate(chunks):
        r = c.req({"op": "tour_set", "wps": ch, "reset": j == 0, "save": j == len(chunks) - 1})
    return len(W), sum(w[6] for w in W) / 20, r

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "upload": print("%d waypoints, %.0fs per loop, %s" % upload())
    else:
        c = Conn()
        if cmd == "start": print(c.req({"op": "tour_start", "player": sys.argv[2]}))
        elif cmd == "stop": print(c.req({"op": "tour_stop"}))
        elif cmd == "status": print(c.req({"op": "tour_status"}))

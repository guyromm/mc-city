#!/usr/bin/env python3
"""Direct (non-puppet) build of a module's model: fastbuild.py rotunda|park|hall"""
import importlib, sys, time
from tower import Model, Conn, boxes, send_fill
import puppet
mod = importlib.import_module(sys.argv[1])
m = mod.build(Model())
c = Conn()
for cmd in getattr(mod, "SETUP", []): print(c.req(cmd))
time.sleep(1)
t0 = time.time()
bx = boxes(m.v)
placed, errs = send_fill(c, bx)
print(f"{sys.argv[1]}: {len(bx)} boxes, {placed} blocks changed, {len(errs)} errors {errs[:3]} in {time.time()-t0:.1f}s")
x1, x2, z1, z2 = (min(p[0] for p in m.v), max(p[0] for p in m.v), min(p[2] for p in m.v), max(p[2] for p in m.v))
bad = puppet.verify(c, m, x1, x2, z1, z2)
print(f"verify: {len(bad)} mismatches", bad[:6])

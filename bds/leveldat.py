#!/usr/bin/env python3
"""Minimal Bedrock level.dat (little-endian NBT) read/patch tool.
usage: leveldat.py level.dat show
       leveldat.py level.dat set key=TYPE:value ...   (TYPE: b,i,l,s,str; dotted path for compounds)
"""
import struct, sys, json

END, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE, BARR, STR, LIST, COMP, IARR, LARR = range(13)

class R:
    def __init__(s, b): s.b, s.p = b, 0
    def u(s, f):
        v = struct.unpack_from("<" + f, s.b, s.p); s.p += struct.calcsize("<" + f); return v[0]
    def str(s):
        n = s.u("H"); v = s.b[s.p:s.p + n].decode("utf-8", "surrogateescape"); s.p += n; return v
    def payload(s, t):
        if t == BYTE: return s.u("b")
        if t == SHORT: return s.u("h")
        if t == INT: return s.u("i")
        if t == LONG: return s.u("q")
        if t == FLOAT: return s.u("f")
        if t == DOUBLE: return s.u("d")
        if t == BARR: n = s.u("i"); v = list(s.b[s.p:s.p + n]); s.p += n; return v
        if t == STR: return s.str()
        if t == LIST:
            et = s.u("B"); n = s.u("i"); return (et, [s.payload(et) for _ in range(n)])
        if t == COMP:
            d = {}
            while (tt := s.u("B")) != END:
                k = s.str(); d[k] = (tt, s.payload(tt))
            return d
        if t == IARR: n = s.u("i"); return [s.u("i") for _ in range(n)]
        if t == LARR: n = s.u("i"); return [s.u("q") for _ in range(n)]
        raise ValueError(t)

def w_payload(t, v):
    if t == BYTE: return struct.pack("<b", v)
    if t == SHORT: return struct.pack("<h", v)
    if t == INT: return struct.pack("<i", v)
    if t == LONG: return struct.pack("<q", v)
    if t == FLOAT: return struct.pack("<f", v)
    if t == DOUBLE: return struct.pack("<d", v)
    if t == BARR: return struct.pack("<i", len(v)) + bytes(v)
    if t == STR: e = v.encode("utf-8", "surrogateescape"); return struct.pack("<H", len(e)) + e
    if t == LIST: et, items = v; return struct.pack("<Bi", et, len(items)) + b"".join(w_payload(et, i) for i in items)
    if t == COMP:
        out = b""
        for k, (tt, vv) in v.items(): out += struct.pack("<B", tt) + w_payload(STR, k) + w_payload(tt, vv)
        return out + b"\x00"
    if t == IARR: return struct.pack("<i", len(v)) + b"".join(struct.pack("<i", i) for i in v)
    if t == LARR: return struct.pack("<i", len(v)) + b"".join(struct.pack("<q", i) for i in v)

def load(path):
    b = open(path, "rb").read()
    ver, ln = struct.unpack_from("<ii", b, 0)
    r = R(b[8:8 + ln]); t = r.u("B"); name = r.str()
    return ver, name, r.payload(t)

def save(path, ver, name, root):
    body = struct.pack("<B", COMP) + w_payload(STR, name) + w_payload(COMP, root)
    open(path, "wb").write(struct.pack("<ii", ver, len(body)) + body)

def plain(v):
    t, x = v
    if t == COMP: return {k: plain(vv) for k, vv in x.items()}
    if t == LIST: return [plain((x[0], i)) for i in x[1]]
    return x

TYPES = {"b": BYTE, "i": INT, "l": LONG, "s": SHORT, "str": STR}
if __name__ == "__main__":
    path, cmd, *args = sys.argv[1:]
    ver, name, root = load(path)
    if cmd == "show":
        print(json.dumps(plain((COMP, root)), indent=1, default=str)); sys.exit()
    for a in args:
        key, tv = a.split("=", 1); ty, val = tv.split(":", 1); t = TYPES[ty]
        val = val if t == STR else int(val)
        node = root; *parents, leaf = key.split(".")
        for p in parents:
            node = node.setdefault(p, (COMP, {}))[1]
        node[leaf] = (t, val)
    save(path, ver, name, root)
    print("patched", args)

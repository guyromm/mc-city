#!/usr/bin/env python3
"""mcs.py 'raw command' | mcs.py '{"op":"ping"}'  -> talks to bds.py control port"""
import socket, sys, json
s = socket.create_connection(("127.0.0.1", 8767)); f = s.makefile("rw")
for c in (sys.argv[1:] or [l.strip() for l in sys.stdin if l.strip()]):
    f.write(c + "\n"); f.flush(); print(f.readline().strip())

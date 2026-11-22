#!/usr/bin/env python3
"""Usage: mc.py 'cmd1' 'cmd2' ...   (or pipe commands on stdin, one per line)"""
import socket, sys
cmds = sys.argv[1:] or [l.strip() for l in sys.stdin if l.strip()]
s = socket.create_connection(("127.0.0.1", 8766)); f = s.makefile("rw")
for c in cmds:
    f.write(c.lstrip("/") + "\n"); f.flush(); print(c, "->", f.readline().strip())

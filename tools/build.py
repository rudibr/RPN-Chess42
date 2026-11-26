#!/usr/bin/env python3
"""Build CHESS.raw and CHESS_listing.txt from the generator sources.

Usage (from the tools folder):  python3 build.py
"""
import subprocess
import sys
from sim42 import encode, parse
from decode42 import decode

subprocess.run([sys.executable, "gen3.py", "chess3.txt"], check=True)
text = open("chess3.txt").read()
raw = encode(text)
assert decode(raw) == [l for p in parse(text) for l in p], "encode/decode round trip failed"
open("../CHESS.raw", "wb").write(raw)
open("../CHESS_listing.txt", "w").write(text)
print(f"CHESS.raw: {len(raw)} bytes")

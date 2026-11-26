#!/usr/bin/env python3
"""DM42 chess, two programs: "CHESS" (engine + new game) and "CHCON" (graphical UI).
Only those two global labels exist. CHCON calls engine services by setting flag 06,
putting a service code in R38 and doing XEQ "CHESS"."""
import re
import sys
import gen_listing as G
from gfx import sprite_list, strips, glyph, FONT_SRC

SVC = {"ChGEN0": 1, "ChMAKE": 2, "ChMCHK": 3, "ChUNMK": 4, "ChSRCH": 5,
       "ChHASMV": 6, "ChINCHK": 7, "ChRESC": 8}


def svc(name):
    return ["SF 06", str(SVC[name]), "STO 38", 'XEQ "CHESS"']


# ------------------------------------------------------------ helpers
def esc(bs):
    out = ""
    for b in bs:
        if b == 10:
            out += "[LF]"
        elif 32 <= b <= 126 and chr(b) not in '"[]':
            out += chr(b)
        else:
            out += f"[x{b:02X}]"
    return out


def lit(bs, append=False):
    bs = bytes(bs)
    out = []
    first = not append
    if first and bs[0] >= 0x7F:
        out.append("CLA")
        first = False
    while bs:
        n = 15 if first else 14
        chunk, bs = bs[:n], bs[n:]
        out.append(("" if first else "├") + '"' + esc(chunk) + '"')
        first = False
    return out


def agraph_at(bs, y, x):
    out = []
    for i in range(0, len(bs), 42):
        out += lit(bs[i:i + 42]) + [str(y), str(x + i), "AGRAPH"]
    return out


def big_glyph(c):
    """2x scaled 5x7 glyph -> (top 12 bytes, bottom 12 bytes)"""
    rows = FONT_SRC[c].split("|")
    top, bot = [], []
    for x in range(6):
        col = 0
        if x > 0:
            for y in range(7):
                if rows[y][x - 1] == '#':
                    col |= 3 << (2 * y)       # 14-bit column
        for _ in range(2):
            top.append(col & 0xFF)
            bot.append(col >> 8)
    return bytes(top), bytes(bot)


def big_bytes(s):
    t = b"".join(big_glyph(c)[0] for c in s)
    b = b"".join(big_glyph(c)[1] for c in s)
    return t, b


def big_at(s, y, x):
    t, b = big_bytes(s)
    out = agraph_at(t, y, x)
    if any(b):
        out += agraph_at(b, y + 8, x)
    return out


# ------------------------------------------------------------ engine program
def localize(prog_lines, tag):
    """numeric local labels -> @tag_n ; "ChXXX" globals -> @ChXXX ; drop END"""
    out = []
    for l in prog_lines:
        if l == "END":
            continue
        m = re.fullmatch(r'(LBL|GTO|XEQ) (\d\d)', l)
        if m:
            out.append(f"{m.group(1)} @{tag}_{m.group(2)}")
            continue
        m = re.fullmatch(r'(LBL|GTO|XEQ) "(Ch\w+)"', l)
        if m:
            out.append(f"{m.group(1)} @{m.group(2)}")
            continue
        out.append(l)
    return out


engine = [
    'LBL "CHESS"',
    "FS?C 06", "GTO @SVC",
    "SIZE 1224",
    "XEQ @ChCINIT",
    "XEQ @ChSETUP",
    "0", "STO 49", "STO 54",
    "1", "STO 53",
    "125", "STO 83",
    "SF 07",
    'GTO "CHCON"',
    "LBL @SVC",
    "RCL 38",
]
for name, k in SVC.items():
    engine += [str(k), "X=Y?", f"GTO @{name}", "R↓"]
engine += ["RTN"]
for tag, prog in (("ci", G.cinit), ("se", G.srch), ("ge", G.gen), ("ma", G.make)):
    engine += localize(G.split_strings(prog), tag)
engine += ["END"]

# ------------------------------------------------------------ UI program
PX = 231
Y = [14 + 18 * i for i in range(12)]
MSGS = {1: "Your move", 2: "Thinking...", 3: "Illegal move", 4: "Check!",
        5: "Mate - I win", 6: "Mate - you win", 7: "Stalemate", 8: "Pick own piece"}
DASH_T, DASH_B = big_glyph('-')

ui = [
    'LBL "CHCON"',
    "FS?C 07", "XEQ @UINIT",
    "LBL @REDRAW",
    "3", 'STO "GrMod"',
    "XEQ @DRAW",
    "LBL @KEY",
    "GETKEY",
    "STO 55",
    "13", "X=Y?", "GTO @ENTER",
    "RCL 55", "20", "X=Y?", "GTO @UP",       # 8
    "RCL 55", "30", "X=Y?", "GTO @DOWN",     # 2
    "RCL 55", "24", "X=Y?", "GTO @LEFT",     # 4
    "RCL 55", "26", "X=Y?", "GTO @RIGHT",    # 6
    "RCL 55", "17", "X=Y?", "GTO @CLEAR",    # <-
    "RCL 55", "34", "X=Y?", "GTO @ENGINE",   # 0
    "RCL 55", "21", "X=Y?", "GTO @LEVEL",    # 9
    "RCL 55", "33", "X=Y?", "GTO @QUIT",     # EXIT
    "GTO @KEY",
    "LBL @UP", "10", "GTO @MOVE",
    "LBL @DOWN", "10", "+/-", "GTO @MOVE",
    "LBL @LEFT", "1", "+/-", "GTO @MOVE",
    "LBL @RIGHT", "1",
    "LBL @MOVE",
    "RCL 83", "+", "STO 39",
    "RCL IND 39", "0.5", "X=Y?", "GTO @KEY",
    "RCL 39", "STO 83",
    "GTO @REDRAW",
    "LBL @ENTER",
    "RCL 49", "X≠0?", "GTO @DEST",
    "RCL IND 83", "RCL 05", "×", "1", "X>Y?", "GTO @NOTOWN",
    "RCL 83", "STO 50",
    "1", "STO 49", "STO 53",
    "GTO @REDRAW",
    "LBL @NOTOWN",
    "8", "STO 53",
    "GTO @REDRAW",
    "LBL @DEST",
    "RCL 83", "RCL 50", "X=Y?", "GTO @CLEAR",
    "0", "STO 49",
    "RCL 50", "1000", "×", "RCL 83", "+", "STO 21",
    *svc("ChGEN0"),
    "RCL 30", "STO 18",
    "LBL @SCAN",
    "RCL 18", "RCL 19", "X≠Y?", "GTO @SCAN2",
    "RCL 20", "STO 18",
    "LBL @SCAN2",
    "RCL 30", "80", "+", "RCL 18", "X=Y?", "GTO @ILLEGAL",
    "RCL IND ST X", "1000000", "MOD", "RCL 21", "X=Y?", "GTO @FOUND",
    "1", "STO+ 18", "GTO @SCAN",
    "LBL @FOUND",
    *svc("ChMAKE"),
    *svc("ChMCHK"),
    "FC? 03", "GTO @LEGAL",
    *svc("ChUNMK"),
    "LBL @ILLEGAL",
    "3", "STO 53",
    "GTO @REDRAW",
    "LBL @LEGAL",
    "RCL 21", "STO 54",
    "GTO @ENGINE",
    "LBL @LEVEL",
    "RCL 33", "3", "MOD", "1", "+", "STO 33",
    "GTO @REDRAW",
    "LBL @CLEAR",
    "0", "STO 49",
    "GTO @REDRAW",
    "LBL @QUIT",
    "CLLCD",
    "0", 'STO "GrMod"',
    '"XEQ CHCON to"',
    '├"[LF]continue"',
    "AVIEW",
    "RTN",
    # ---- computer move
    "LBL @ENGINE",
    "0", "STO 49",
    "2", "STO 53",
    "3", 'STO "GrMod"',
    "XEQ @DRAW",
    *svc("ChSRCH"),
    "RCL 35", "STO 32",
    "RCL 31",
    "X=0?", "GTO @NOMOVE",
    "STO 21", "STO 54",
    *svc("ChMAKE"),
    *svc("ChHASMV"),
    *svc("ChINCHK"),
    "1", "STO 53",
    "FS? 03", "XEQ @SETCHK",
    "FC? 05", "XEQ @SETEND",
    "GTO @REDRAW",
    "LBL @SETCHK", "4", "STO 53", "RTN",
    "LBL @SETEND", "7", "STO 53", "FS? 03", "XEQ @SETMATE", "RTN",
    "LBL @SETMATE", "5", "STO 53", "RTN",
    "LBL @NOMOVE",
    *svc("ChINCHK"),
    "7", "STO 53",
    "FS? 03", "XEQ @SETWIN",
    "GTO @REDRAW",
    "LBL @SETWIN", "6", "STO 53", "RTN",
    # ---- full screen redraw
    "LBL @DRAW",
    "CLLCD",
    "1", "STO 84",
    "LBL @DR1",
    "1", "STO 85",
    "LBL @DR2",
    "RCL 84", "10", "×", "RCL 85", "+", "110", "+", "STO 39",
    "XEQ @SQXY",
    "RCL IND 39", "ABS", "IP", "RCL IND 39", "SIGN", "×", "6", "+", "2", "×",
    "RCL 84", "RCL 85", "+", "2", "MOD", "1", "X<>Y", "-", "+",
    "STO 13",
    "12", "X≠Y?", "XEQ @SPR",
    "1", "STO+ 85", "RCL 85", "9", "X≠Y?", "GTO @DR2",
    "1", "STO+ 84", "RCL 84", "9", "X≠Y?", "GTO @DR1",
    "RCL 54", "X=0?", "GTO @DR3",
    "1000", "÷", "IP", "STO 39", "XEQ @SQXY", "27", "STO 13", "XEQ @SPR",
    "RCL 54", "1000", "MOD", "STO 39", "XEQ @SQXY", "27", "STO 13", "XEQ @SPR",
    "LBL @DR3",
    "RCL 83", "STO 39", "XEQ @SQXY", "26", "STO 13", "XEQ @SPR",
    "RCL 49", "X=0?", "GTO @DR4",
    "RCL 50", "STO 39", "XEQ @SQXY", "28", "STO 13", "XEQ @SPR",
    "LBL @DR4",
    # border
    *lit(bytes([1] * 42)),
    "15", "STO 52",
    "LBL @BRD1",
    "15", "RCL 52", "AGRAPH",
    "224", "RCL 52", "AGRAPH",
    "42", "STO+ 52",
    "RCL 52", "225", "X>Y?", "GTO @BRD1",
    *lit(bytes([255])),
    "16", "STO 51",
    "LBL @BRD2",
    "RCL 51", "15", "AGRAPH",
    "RCL 51", "224", "AGRAPH",
    "8", "STO+ 51",
    "RCL 51", "224", "X>Y?", "GTO @BRD2",
    # coordinates (small font)
    "1", "STO 84",
    "LBL @CRD",
    "CLA", "RCL 84", "1150", "+", "STO 39", "ARCL IND 39",
    "224", "RCL 84", "26", "×", "-", "9", "+", "3", "AGRAPH",
    "CLA", "RCL 84", "1140", "+", "STO 39", "ARCL IND 39",
    "228", "RCL 84", "26", "×", "1", "-", "AGRAPH",
    "1", "STO+ 84", "RCL 84", "9", "X≠Y?", "GTO @CRD",
    # panel (large font)
    *big_at("Level", Y[0], PX),
    str(Y[0]), "STO 51", str(PX + 72), "STO 52",
    "RCL 33", "4", "×", "1188", "+", "XEQ @BIG1",
]
for k in MSGS:
    ui += ["RCL 53", str(k), "X=Y?", f"XEQ @MSG{k}"]
ui += [
    *big_at("Last:", Y[2], PX),
    "RCL 54", "X=0?", "GTO @PN1",
    str(Y[2]), "STO 51", str(PX + 72), "STO 52",
    "RCL 54", "1000", "÷", "IP", "XEQ @SQB",
    "RCL 54", "1000", "MOD", "XEQ @SQB",
    "LBL @PN1",
    *big_at("Move:", Y[3], PX),
    str(Y[3]), "STO 51", str(PX + 72), "STO 52",
    "RCL 49", "X=0?", "GTO @PN2",
    "RCL 50", "XEQ @SQB",
    *lit(DASH_T), "RCL 51", "RCL 52", "AGRAPH",
    *lit(DASH_B), "RCL 51", "8", "+", "RCL 52", "AGRAPH",
    "12", "STO+ 52",
    "LBL @PN2",
    "RCL 83", "XEQ @SQB",
    *big_at("8/2 up/down", Y[4], PX),
    *big_at("4/6 left/right", Y[5], PX),
    *big_at("ENTER select", Y[6], PX),
    *big_at("<- clear", Y[7], PX),
    *big_at("0 play for me", Y[8], PX),
    *big_at("9 level", Y[9], PX),
    *big_at("EXIT quit", Y[10], PX),
    *big_at("XEQ CHESS new", Y[11], PX),
    "RTN",
    # square R39 -> R51 row, R52 column
    "LBL @SQXY",
    "RCL 39", "10", "÷", "IP", "11", "-", "26", "×", "224", "X<>Y", "-", "STO 51",
    "RCL 39", "10", "MOD", "26", "×", "10", "-", "STO 52",
    "RTN",
    # draw square name X (e.g. e4) in large font at R51/R52, advance R52
    "LBL @SQB",
    "STO 04",
    "10", "MOD", "4", "×", "1156", "+", "XEQ @BIG1",
    "RCL 04", "10", "÷", "IP", "4", "×", "1144", "+",
    # draw one large glyph whose 4 registers start at X
    "LBL @BIG1",
    "STO 03",
    "CLA", "ARCL IND 03", "1", "STO+ 03", "ARCL IND 03",
    "RCL 51", "RCL 52", "AGRAPH",
    "1", "STO+ 03",
    "CLA", "ARCL IND 03", "1", "STO+ 03", "ARCL IND 03",
    "RCL 51", "8", "+", "RCL 52", "AGRAPH",
    "12", "STO+ 52",
    "RTN",
]
for k, m in MSGS.items():
    ui += [f"LBL @MSG{k}"] + big_at(m, Y[1], PX) + ["RTN"]

# one-time tables: small glyphs (board coordinates) and large glyphs (panel)
ui += ["LBL @UINIT", "1141", "STO 03"]
for c in "abcdefgh":
    ui += lit(glyph(c)) + ["ASTO IND 03", "1", "STO+ 03"]
ui += ["1151", "STO 03"]
for c in "12345678":
    ui += lit(glyph(c)) + ["ASTO IND 03", "1", "STO+ 03"]
ui += ["1160", "STO 03"]          # large glyphs: a-h at 1160.., 1-8 at 1192..
for c in "abcdefgh12345678":
    t, b = big_glyph(c)
    for part in (t[:6], t[6:], b[:6], b[6:]):
        ui += lit(part) + ["ASTO IND 03", "1", "STO+ 03"]
ui += ["RTN"]

# sprites: R13 = code, R51/R52 = square origin
sp = sprite_list()
codes = sorted(sp)
_n = iter(range(1000))


def tree(cs):
    if len(cs) == 1:
        return [f"GTO @S{cs[0]}"]
    mid = len(cs) // 2
    right = f"@T{next(_n)}"
    return (["RCL 13", str(cs[mid]), "X≤Y?", f"GTO {right}"] + tree(cs[:mid])
            + [f"LBL {right}"] + tree(cs[mid:]))


ui += ["LBL @SPR"] + tree(codes)
for c in codes:
    ui.append(f"LBL @S{c}")
    for (j, a, bs) in strips(sp[c]):
        ui += lit(bs)
        ui += ["RCL 51"] + ([str(j), "+"] if j else [])
        ui += ["RCL 52"] + ([str(a), "+"] if a else [])
        ui += ["AGRAPH"]
    ui.append("RTN")
ui += ["END"]


# ------------------------------------------------------------ assign label numbers
POOL = [f"{n:02d}" for n in range(15, 100)] + list("ABCDEFGHIJabcde") + [f"{n:02d}" for n in range(0, 15)]


def assign(prog):
    names = []
    for l in prog:
        m = re.fullmatch(r'LBL (@\S+)', l)
        if m:
            assert m.group(1) not in names, m.group(1)
            names.append(m.group(1))
    assert len(names) <= len(POOL), (prog[0], len(names))
    mp = dict(zip(names, POOL))
    out = []
    for l in prog:
        m = re.fullmatch(r'(LBL|GTO|XEQ) (@\S+)', l)
        if m:
            assert m.group(2) in mp, l
            l = f"{m.group(1)} {mp[m.group(2)]}"
        out.append(l)
    return out, len(names)


ENG, ne = assign(engine)
UI, nu = assign(ui)
ALL = ENG + UI

if __name__ == "__main__":
    print("labels: CHESS", ne, " CHCON", nu, "(max 115)", file=sys.stderr)
    open(sys.argv[1] if len(sys.argv) > 1 else "chess3.txt", "w").write("\n".join(ALL) + "\n")

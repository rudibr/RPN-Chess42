#!/usr/bin/env python3
"""Generates the HP-42S / DM42 chess program listing (chess42.txt).

Register map
  R00-R04 temps (PST args/temps)   R05 SD side to move (+1 White, -1 Black)
  R06 S  score (White's view)      R07 EP  en-passant target square (0 = none)
  R08 CR castling rights (1=WK 2=WQ 4=BK 8=BQ)
  R09 white king sq  R10 black king sq   R11 P ply   R12 ptr   R13 temp
  R14-R30 node record: A B BS D I CE QS M FR TO PC CP OEP OCR OS SPC LB
  R31 best root move  R32 root score  R33 level (search depth)  R34 ray dir (ATT)
  R35 V return value  R36 node counter  R39 temp
  R40-R47 king/queen directions, R48-R55 knight jumps
  R56-R62 move generator scratch, R63-R69 attack test scratch
  R70-R75 piece values, R76-R81 positional weights
  R83-R85 board display scratch
  R100-R219  10x12 mailbox board (square = 100 + index, a1 = 121, h8 = 198)
             piece = side*(type + k/100), type P1 N2 B3 R4 Q5 K6, k = piece-list slot,
             off-board = 0.5
  R220-R355  saved node records (17 per ply, 8 plies)
  R360-R999  move lists (80 per ply)
  R1001-R1078 centre table (sq+880)
  R1081-R1112 piece list (square of piece k)
  R1120-R1132 piece glyphs, R1141-R1148 file letters, R1151-R1158 rank digits
"""

import re
LF = "[LF]"


def P(*lines):
    out = []
    for l in lines:
        out.extend(l.strip().split("\n") if "\n" in l else [l])
    return [x.strip() for x in out if x.strip()]


chess = P(
    'LBL "CHESS"',
    "SIZE 1160",
    'XEQ "ChCINIT"',
    "LBL 15",                # new game
    'XEQ "ChSETUP"',
    '"New game"',
    "GTO 17",
    "LBL 16",
    "CLA",
    "LBL 17",                # prompt
    f'├"{LF}Move? e2e4=5254"',
    "1", "+/-",
    "PROMPT",
    "X<0?", "GTO 18",        # R/S alone: show board
    "X=0?", "GTO 19",        # 0: computer moves
    "9", "X=Y?", "GTO 15",   # 9: new game
    "R↓",
    "10", "X>Y?", "GTO 20",  # 1-8: level
    "R↓",
    # ---- parse move abcd -> from/to squares
    "STO 00",
    "1000", "÷", "IP", "STO 01",
    "RCL 00", "100", "÷", "IP", "10", "MOD", "10", "×", "STO+ 01",
    "110", "STO+ 01",
    "RCL 00", "10", "÷", "IP", "10", "MOD", "STO 02",
    "RCL 00", "10", "MOD", "10", "×", "110", "+", "STO+ 02",
    "RCL 01", "1000", "×", "RCL 02", "+", "STO 21",
    'XEQ "ChGEN0"',
    "RCL 30", "STO 18",
    "LBL 21",
    "RCL 18", "RCL 19", "X≠Y?", "GTO 22",
    "RCL 20", "STO 18",
    "LBL 22",
    "RCL 30", "80", "+", "RCL 18", "X=Y?", "GTO 29",
    "RCL IND ST X", "1000000", "MOD", "RCL 21", "X=Y?", "GTO 28",
    "1", "STO+ 18", "GTO 21",
    "LBL 28",
    'XEQ "ChMAKE"',
    'XEQ "ChMCHK"',
    "FC? 03", "GTO 19",
    'XEQ "ChUNMK"',
    "LBL 29",
    '"Illegal move"',
    "GTO 17",
    # ---- level
    "LBL 20",
    "R↓",
    "3", "X>Y?", "X<>Y",
    "STO 33",
    "1150", "+", "STO 03",
    '"Level "',
    "ARCL IND 03",
    "GTO 17",
    # ---- computer move
    "LBL 19",
    '"Thinking..."',
    "AVIEW",
    'XEQ "ChSRCH"',
    "RCL 35", "STO 32",
    "RCL 31",
    "X=0?", "GTO 23",
    "STO 21",
    '"I play "',
    'XEQ "ChMV2A"',
    'XEQ "ChMAKE"',
    'XEQ "ChHASMV"',
    'XEQ "ChINCHK"',
    "FS? 03",
    '├"+"',
    "FC? 05",
    "GTO 24",
    '├" "',
    "FIX 02",
    "RCL 32", "100", "÷",
    "ARCL ST X",
    "GTO 17",
    "LBL 24",                # human has no legal move
    "FS? 03",
    '"Mate - I win"',
    "FC? 03",
    '"Stalemate"',
    "GTO 17",
    "LBL 23",                # computer has no legal move
    'XEQ "ChINCHK"',
    "FS? 03",
    '"Mate - you win"',
    "FC? 03",
    '"Stalemate"',
    "GTO 17",
    # ---- board display, two ranks per screen
    "LBL 18",
    "8", "STO 83",
    "LBL 25",
    "CLA",
    "XEQ 26",
    f'├"{LF}"',
    "1", "STO- 83",
    "XEQ 26",
    "PROMPT",
    "1", "STO- 83",
    "RCL 83",
    "X>0?", "GTO 25",
    "GTO 16",
    "LBL 26",                # append rank R83
    "RCL 83", "1150", "+", "STO 03",
    "ARCL IND 03",
    "RCL 83", "10", "×", "110", "+", "STO 84",
    "LBL 27",
    "1", "STO+ 84",
    "RCL IND 84", "ABS", "IP",
    "RCL IND 84", "SIGN", "×",
    "1126", "+", "STO 03",
    "ARCL IND 03",
    "RCL 84", "10", "MOD", "8", "X≠Y?", "GTO 27",
    "RTN",
    # ---- append move R21 as text
    'LBL "ChMV2A"',
    "RCL 21", "1000", "÷", "IP", "XEQ 30",
    "RCL 21", "1000", "MOD",
    "LBL 30",
    "STO 04",
    "10", "MOD", "1140", "+", "STO 03",
    "ARCL IND 03",
    "RCL 04", "10", "÷", "IP", "1139", "+", "STO 03",
    "ARCL IND 03",
    "RTN",
    "END",
)

# ---------------- constants / setup ----------------
glyphs = [" k", " q", " r", " b", " n", " p", " .", " P", " N", " B", " R", " Q", " K"]
cinit = P(
    'LBL "ChCINIT"',
    "1", "STO 40", "+/-", "STO 41",
    "10", "STO 42", "+/-", "STO 43",
    "9", "STO 44", "+/-", "STO 45",
    "11", "STO 46", "+/-", "STO 47",
    "0", "STO 48", "STO 94", "STO 99",
    "8", "STO 86", "+/-", "STO 87",
    "12", "STO 88", "+/-", "STO 89",
    "19", "STO 90", "+/-", "STO 91",
    "21", "STO 92", "+/-", "STO 93",
    "1", "STO 95", "+/-", "STO 96",
    "10", "STO 97", "+/-", "STO 98",
    "100", "STO 70", "300", "STO 71", "320", "STO 72",
    "500", "STO 73", "900", "STO 74", "0", "STO 75",
    "STO 76", "STO 79", "4", "STO 77", "2", "STO 78", "1", "STO 80",
    "4", "+/-", "STO 81",
    "2", "STO 33",
)
cinit += P(
    # centre table C = 7 - (|2f-9| + |2r-9|)/2 at R(sq+880)
    "1", "STO 00",
    "LBL 15",
    "1", "STO 01",
    "LBL 16",
    "RCL 01", "2", "×", "9", "-", "ABS",
    "RCL 00", "2", "×", "9", "-", "ABS",
    "+", "2", "÷", "7", "X<>Y", "-",
    "RCL 00", "10", "×", "RCL 01", "+", "990", "+",
    "X<>Y", "STO IND ST Y",
    "1", "STO+ 01", "RCL 01", "9", "X≠Y?", "GTO 16",
    "1", "STO+ 00", "RCL 00", "9", "X≠Y?", "GTO 15",
    "RTN",
    # ---- initial position
    'LBL "ChSETUP"',
    "100", "STO 03",
    "LBL 17",
    "0.5", "STO IND 03",
    "1", "STO+ 03", "RCL 03", "220", "X≠Y?", "GTO 17",
    "1", "STO 00",
    "LBL 18",
    "1", "STO 01",
    "LBL 19",
    "RCL 00", "10", "×", "RCL 01", "+", "110", "+", "STO 03",
    "0", "STO IND 03",
    "1", "STO+ 01", "RCL 01", "9", "X≠Y?", "GTO 19",
    "1", "STO+ 00", "RCL 00", "9", "X≠Y?", "GTO 18",
    "42356324", "STO 04",
    "8", "STO 01",
    "LBL 20",
    "RCL 04", "10", "MOD", "STO 02",
    "RCL 04", "10", "÷", "IP", "STO 04",
    # white piece
    "RCL 01", "120", "+", "STO 03",
    "RCL 01", "100", "÷", "RCL 02", "+", "STO IND 03",
    "RCL 01", "1080", "+", "STO 13", "RCL 03", "STO IND 13",
    # white pawn
    "RCL 01", "130", "+", "STO 03",
    "RCL 01", "8", "+", "100", "÷", "1", "+", "STO IND 03",
    "RCL 01", "1088", "+", "STO 13", "RCL 03", "STO IND 13",
    # black piece
    "RCL 01", "190", "+", "STO 03",
    "RCL 01", "16", "+", "100", "÷", "RCL 02", "+", "+/-", "STO IND 03",
    "RCL 01", "1096", "+", "STO 13", "RCL 03", "STO IND 13",
    # black pawn
    "RCL 01", "180", "+", "STO 03",
    "RCL 01", "24", "+", "100", "÷", "1", "+", "+/-", "STO IND 03",
    "RCL 01", "1104", "+", "STO 13", "RCL 03", "STO IND 13",
    "1", "STO- 01", "RCL 01", "X≠0?", "GTO 20",
    "1", "STO 05",
    "0", "STO 06", "STO 07", "STO 31",
    "15", "STO 08",
    "125", "STO 09",
    "195", "STO 10",
    "RTN",
    "END",
)

# ---------------- search ----------------
FIELDS = list(range(14, 31))
spill = P('LBL "ChSPILL"', "RCL 11", "17", "×", "220", "+", "STO 12")
for r in FIELDS:
    spill += [f"RCL {r:02d}", "STO IND 12", "1", "STO+ 12"]
spill += ["RTN"]
resto = P('LBL "ChRESTO"', "RCL 11", "17", "×", "220", "+", "STO 12")
for r in FIELDS:
    resto += ["RCL IND 12", f"STO {r:02d}", "1", "STO+ 12"]
resto += ["RTN"]

srch = P(
    'LBL "ChSRCH"',
    "0", "STO 11", "STO 31", "STO 36",
    "30000", "STO 15", "+/-", "STO 14",
    "RCL 33", "STO 17",
    "LBL 30",                     # node entry
    "1", "STO+ 36",
    "RCL 11", "80", "×", "360", "+", "STO 30",
    "RCL 17", "X>0?", "GTO 31",
    "SF 01",                      # quiescence node
    "RCL 06", "RCL 05", "×", "STO 16", "STO 35",
    "RCL 11", "RCL 33", "4", "+", "X≤Y?", "GTO 32",
    "RCL 16", "RCL 15", "X≤Y?", "GTO 32",
    "RCL 14", "RCL 16", "X>Y?", "STO 14",
    "GTO 33",
    "LBL 31",
    "CF 01",
    "20000", "+/-", "STO 16",
    "LBL 33",
    'XEQ "ChGEN"',
    "FS? 02", "GTO 34",
    "RCL 30", "STO 18",
    "LBL 35",                     # move loop
    "RCL 18", "RCL 19", "X≠Y?", "GTO 36",
    "RCL 20", "STO 18",
    "LBL 36",
    "RCL 30", "80", "+", "RCL 18", "X=Y?", "GTO 37",
    "RCL IND ST X", "STO 13",
    "RCL 17", "X>0?", "GTO 40",
    "RCL 13", "10000000", "÷", "IP", "69", "+", "STO 39",   # delta pruning
    "RCL IND 39", "RCL 06", "RCL 05", "×", "+", "200", "+",
    "RCL 14", "X<Y?", "GTO 41",
    "GTO 37",
    "LBL 41",                     # losing-looking capture onto a defended square: skip
    "RCL 13", "1000000", "÷", "IP", "10", "MOD", "7", "X<>Y", "-", "69", "+", "STO 39",
    "RCL IND 39",
    "RCL 13", "10000000", "÷", "IP", "69", "+", "STO 39",
    "RCL IND 39", "50", "+",
    "X<Y?", "GTO 42",
    "GTO 40",
    "LBL 42",
    "RCL 13", "1000", "MOD", "STO 63",
    "RCL 05", "+/-", "STO 64",
    'XEQ "ChATT"',
    "FS? 03", "GTO 35",
    "LBL 40",
    "RCL 13", "1000000", "MOD", "STO 21",
    "1", "STO+ 18",
    'XEQ "ChMAKE"',
    'XEQ "ChSPILL"',
    "RCL 15", "+/-", "RCL 14", "+/-", "STO 15", "R↓", "STO 14",
    "1", "STO- 17", "STO+ 11",
    "GTO 30",
    "LBL 34",                     # king can be captured: previous move illegal
    "10000", "STO 35",
    "LBL 32",                     # return V to parent
    "RCL 11", "X=0?", "RTN",
    "1", "STO- 11",
    'XEQ "ChRESTO"',
    'XEQ "ChUNMK"',
    "RCL 35", "+/-", "RCL 16", "X<Y?", "GTO 38",
    "GTO 39",
    "LBL 38",
    "X<>Y", "STO 16",
    "RCL 11", "X≠0?", "GTO 39",
    "RCL 21", "STO 31",
    "LBL 39",
    "RCL 14", "RCL 35", "+/-", "X>Y?", "STO 14",
    "RCL 15", "RCL 14", "X<Y?", "GTO 35",
    "LBL 37",                     # node finished
    "RCL 16", "STO 35",
    "RCL 17", "X≤0?", "GTO 32",
    "RCL 16", "10000", "+/-", "X<Y?", "GTO 32",
    "0", "STO 35",                # no legal move: mate or stalemate
    "RCL 11", "X=0?", "STO 31",
    'XEQ "ChINCHK"',
    "FC? 03", "GTO 32",
    "RCL 11", "9000", "-", "STO 35",
    "GTO 32",
) + spill + resto + P(
    'LBL "ChINCHK"',                # flag 03: side to move is in check
    "19", "RCL 05", "-", "2", "÷", "RCL IND ST X", "STO 63",
    "RCL 05", "+/-", "STO 64",
    'GTO "ChATT"',
    'LBL "ChMCHK"',                 # after MAKE: flag 03 if mover's king attacked
    "RCL 05", "19", "+", "2", "÷", "RCL IND ST X", "STO 63",
    "RCL 05", "STO 64",
    'GTO "ChATT"',
    'LBL "ChGEN0"',
    "0", "STO 11", "360", "STO 30", "CF 01",
    'GTO "ChGEN"',
    'LBL "ChHASMV"',                # flag 05: side to move has a legal move
    "CF 05",
    'XEQ "ChGEN0"',
    "RCL 30", "STO 18",
    "LBL 15",
    "RCL 18", "RCL 19", "X≠Y?", "GTO 16",
    "RCL 20", "STO 18",
    "LBL 16",
    "RCL 30", "80", "+", "RCL 18", "X=Y?", "RTN",
    "RCL IND ST X", "1000000", "MOD", "STO 21", "1", "STO+ 18",
    'XEQ "ChMAKE"', 'XEQ "ChMCHK"', 'XEQ "ChUNMK"',
    "FC? 03", "SF 05",
    "FS? 05", "RTN",
    "GTO 15",
    "END",
)

# ---------------- move generation & attack test ----------------
gen = P(
    'LBL "ChGEN"',
    "CF 02",
    "RCL 30", "STO 19", "80", "+", "STO 20",
    "RCL 05", "8", "×", "9", "X<>Y", "-", "1080", "+", "STO 61",
    "16", "+", "STO 62",
    "LBL 40",
    "RCL 62", "RCL 61", "X=Y?", "RTN",
    "RCL IND ST X", "1", "STO+ 61", "R↓",
    "X=0?", "GTO 40",
    "STO 56",
    "RCL IND ST X", "ABS", "IP", "STO 82",
    "3", "X>Y?", "GTO 33",
    "X=Y?", "GTO 34",
    "R↓", "5", "X>Y?", "GTO 35",
    "X=Y?", "GTO 36",
    "XEQ 46", "GTO 30",
    "LBL 33",
    "R↓", "1", "X=Y?", "GTO 37",
    "XEQ 42", "GTO 30",
    "LBL 37", "XEQ 41", "GTO 30",
    "LBL 34", "XEQ 43", "GTO 30",
    "LBL 35", "XEQ 44", "GTO 30",
    "LBL 36", "XEQ 45",
    "LBL 30",
    "FS? 02", "RTN",
    "GTO 40",
    # pawn
    "LBL 41",
    "RCL 05", "10", "×", "STO 68",
    "RCL 56", "+", "STO 59",
    "RCL IND 59", "X≠0?", "GTO 57",
    "XEQ 58",
    "RCL 56", "10", "÷", "IP",
    "RCL 05", "2.5", "×", "15.5", "X<>Y", "-",
    "X≠Y?", "GTO 57",
    "RCL 68", "STO+ 59",
    "RCL IND 59", "X=0?", "XEQ 47",
    "LBL 57",
    "RCL 56", "RCL 68", "+", "1", "-", "XEQ 59",
    "FS? 02", "RTN",
    "RCL 56", "RCL 68", "+", "1", "+",
    "LBL 59",                     # pawn capture towards square X
    "STO 59",
    "RCL 07", "X=Y?", "GTO 48",
    "RCL IND 59", "RCL 05", "×",
    "X<0?", "GTO 50",
    "RTN",
    "LBL 48",                     # en passant
    "1", "STO 13", "GTO 49",
    "LBL 58",                     # pawn push: promotions go to the capture list
    "RCL 59", "190", "X<Y?", "GTO 62",
    "RCL 59", "130", "X>Y?", "GTO 62",
    "GTO 47",
    "LBL 62",
    "5", "STO 13", "GTO 49",
    # knight, bishop, rook, queen, king
    "LBL 42", "86", "STO 57", "GTO 56",
    "LBL 43", "44", "STO 57", "GTO 53",
    "LBL 44", "95", "STO 57", "GTO 53",
    "LBL 45", "40", "STO 57", "GTO 53",
    "LBL 46", "40", "STO 57", "XEQ 56",
    "FS? 02", "RTN", "FS? 01", "RTN",
    "RCL 08", "X=0?", "RTN",
    "GTO 60",
    # add quiet move R56 -> R59 (quiet moves fill the list from the top down)
    "LBL 47",
    "FS? 01", "RTN",
    "RCL 20", "RCL 19", "X=Y?", "RTN",
    "1", "STO- 20",
    "RCL 56", "1000", "×", "RCL 59", "+", "STO IND 20",
    "RTN",
    # add capture R56 -> R59, victim type R13; kept sorted by MVV/LVA key
    "LBL 49",
    "RCL 20", "RCL 19", "X=Y?", "RTN",
    "RCL 13", "10", "×", "7", "+", "RCL 82", "-",
    "1000000", "×",
    "RCL 56", "1000", "×", "+", "RCL 59", "+", "STO 13",
    "RCL 19", "STO 39",
    "LBL 63",
    "RCL 39", "RCL 30", "X=Y?", "GTO 64",
    "RCL 39", "1", "-", "RCL IND ST X",
    "RCL 13", "X≤Y?", "GTO 64",
    "R↓", "STO IND 39",
    "1", "STO- 39",
    "GTO 63",
    "LBL 64",
    "RCL 13", "STO IND 39",
    "1", "STO+ 19",
    "RTN",
    # occupied target, X = piece there
    "LBL 50",                     # X = piece*SD <= 0: enemy piece, or edge (-0.5)
    "ABS", "IP",
    "X=0?", "RTN",
    "6", "X=Y?", "SF 02",
    "FS? 02", "RTN",
    "R↓", "STO 13",
    "GTO 49",
    # sliding pieces
    "LBL 53",
    "RCL IND 57",
    "X=0?", "RTN",
    "STO 60",
    "1", "STO+ 57",
    "RCL 56", "STO 59",
    "LBL 55",
    "RCL 60", "STO+ 59",
    "RCL IND 59",
    "X≠0?", "GTO 54",
    "FC? 01", "XEQ 47",
    "GTO 55",
    "LBL 54",
    "RCL 05", "×",
    "X>0?", "GTO 53",
    "XEQ 50",
    "FS? 02", "RTN",
    "GTO 53",
    # stepping pieces
    "LBL 56",
    "RCL IND 57",
    "X=0?", "RTN",
    "1", "STO+ 57", "R↓",
    "RCL 56", "+", "STO 59",
    "RCL IND 59",
    "X=0?", "GTO 52",
    "RCL 05", "×",
    "X>0?", "GTO 56",
    "XEQ 50",
    "FS? 02", "RTN",
    "GTO 56",
    "LBL 52",
    "FC? 01", "XEQ 47",
    "GTO 56",
    # castling
    "LBL 60",
    "RCL 05", "1.5", "×", "2.5", "X<>Y", "-", "STO 39",
    "RCL 08", "X<>Y", "÷", "IP", "2", "MOD", "X=0?", "GTO 61",
    "RCL 56", "1", "+", "RCL IND ST X", "X≠0?", "GTO 61",
    "RCL 56", "2", "+", "RCL IND ST X", "X≠0?", "GTO 61",
    "RCL 05", "+/-", "STO 64",
    "RCL 56", "STO 63", 'XEQ "ChATT"', "FS? 03", "RTN",
    "RCL 56", "1", "+", "STO 63", 'XEQ "ChATT"', "FS? 03", "GTO 61",
    "RCL 56", "2", "+", "STO 59", "XEQ 47",
    "LBL 61",
    "RCL 08", "RCL 39", "2", "×", "÷", "IP", "2", "MOD", "X=0?", "RTN",
    "RCL 56", "1", "-", "RCL IND ST X", "X≠0?", "RTN",
    "RCL 56", "2", "-", "RCL IND ST X", "X≠0?", "RTN",
    "RCL 56", "3", "-", "RCL IND ST X", "X≠0?", "RTN",
    "RCL 05", "+/-", "STO 64",
    "RCL 56", "STO 63", 'XEQ "ChATT"', "FS? 03", "RTN",
    "RCL 56", "1", "-", "STO 63", 'XEQ "ChATT"', "FS? 03", "RTN",
    "RCL 56", "2", "-", "STO 59", "XEQ 47",
    "RTN",
    # ---- is square R63 attacked by side R64?  -> flag 03
    'LBL "ChATT"',
    "CF 03",
    "1", "STO 69",
    "RCL 64", "10", "×", "RCL 63", "X<>Y", "-", "STO 66",
    "1", "-", "XEQ 71",
    "RCL 66", "1", "+", "XEQ 71",
    "FS? 03", "RTN",
    "2", "STO 69", "86", "STO 65", "94", "STO 67", "XEQ 72", "FS? 03", "RTN",
    "6", "STO 69", "40", "STO 65", "48", "STO 67", "XEQ 72", "FS? 03", "RTN",
    "4", "STO 69", "40", "STO 65", "44", "STO 67", "XEQ 74", "FS? 03", "RTN",
    "3", "STO 69", "44", "STO 65", "48", "STO 67", "GTO 74",
    "LBL 71",
    "RCL IND ST X", "RCL 64", "×", "IP", "RCL 69", "X=Y?", "SF 03",
    "RTN",
    "LBL 72",
    "RCL 67", "RCL 65", "X=Y?", "RTN",
    "RCL IND ST X", "RCL 63", "+", "XEQ 71",
    "FS? 03", "RTN",
    "1", "STO+ 65",
    "GTO 72",
    "LBL 74",
    "RCL 67", "RCL 65", "X=Y?", "RTN",
    "RCL IND ST X", "STO 34",
    "RCL 63", "STO 66",
    "LBL 75",
    "RCL 34", "STO+ 66",
    "RCL IND 66", "X=0?", "GTO 75",
    "RCL 64", "×", "IP",
    "5", "X=Y?", "SF 03",
    "R↓",
    "RCL 69", "X=Y?", "SF 03",
    "FS? 03", "RTN",
    "1", "STO+ 65",
    "GTO 74",
    "END",
)

# ---------------- make / unmake / evaluation ----------------
make = P(
    'LBL "ChMAKE"',
    "RCL 06", "STO 28", "RCL 07", "STO 26", "RCL 08", "STO 27",
    "0", "STO 29", "STO 07",
    "RCL 21", "1000", "÷", "IP", "STO 22",
    "RCL 21", "1000", "MOD", "STO 23",
    "RCL IND 22", "STO 24",
    "RCL IND 23", "STO 25",
    "RCL 24", "STO 00", "RCL 22", "STO 01", 'XEQ "ChPST"', "STO- 06",
    "RCL 25", "X=0?", "GTO 80",
    "STO 00", "RCL 23", "STO 01", 'XEQ "ChPST"', "STO- 06",
    "RCL 25", "XEQ 81", "STO 13", "0", "STO IND 13",
    "LBL 80",
    "RCL 24", "ABS", "IP", "1", "X≠Y?", "GTO 82",
    "RCL 23", "RCL 26", "X≠Y?", "GTO 83",
    "RCL 05", "10", "×", "RCL 23", "X<>Y", "-", "STO 39",     # en passant
    "RCL IND 39", "STO 25",
    "STO 00", "RCL 39", "STO 01", 'XEQ "ChPST"', "STO- 06",
    "RCL 25", "XEQ 81", "STO 13", "0", "STO IND 13", "STO IND 39",
    "1", "STO 29",
    "LBL 83",
    "RCL 23", "RCL 22", "-", "ABS", "20", "X≠Y?", "GTO 84",
    "RCL 23", "RCL 22", "+", "2", "÷", "STO 07",
    "LBL 84",
    "RCL 23", "190", "X<Y?", "GTO 85",
    "RCL 23", "130", "X>Y?", "GTO 85",
    "GTO 86",
    "LBL 85",                     # promotion to queen
    "RCL 05", "4", "×", "RCL 24", "+",
    "GTO 87",
    "LBL 82",
    "R↓", "6", "X≠Y?", "GTO 86",
    "19", "RCL 05", "-", "2", "÷", "STO 13", "RCL 23", "STO IND 13",
    "RCL 23", "RCL 22", "-",
    "2", "X=Y?", "GTO 90",
    "+/-", "X=Y?", "GTO 91",
    "GTO 86",
    "LBL 90",
    "RCL 22", "3", "+", "STO 39", "RCL 22", "1", "+", "GTO 92",
    "LBL 91",
    "RCL 22", "4", "-", "STO 39", "RCL 22", "1", "-",
    "LBL 92",
    "STO 03",
    "RCL IND 39", "STO IND 03",
    "XEQ 81", "STO 13", "RCL 03", "STO IND 13",
    "0", "STO IND 39",
    "2", "STO 29",
    "LBL 86",
    "RCL 24",
    "LBL 87",
    "STO IND 23",
    "STO 00", "RCL 23", "STO 01", 'XEQ "ChPST"', "STO+ 06",
    "0", "STO IND 22",
    "RCL 24", "XEQ 81", "STO 13", "RCL 23", "STO IND 13",
    "RCL 08", "X=0?", "GTO 88",
    "RCL 22", "XEQ 89",
    "RCL 23", "XEQ 89",
    "LBL 88",
    "RCL 05", "+/-", "STO 05",
    "RTN",
    "LBL 81",
    "ABS", "FP", "100", "×", "1080", "+",
    "RTN",
    "LBL 89",
    "STO 04",
    "130", "X>Y?", "GTO 72",
    "RCL 04", "190", "X>Y?", "RTN",
    "LBL 72",
    "RCL 04", "121", "X=Y?", "GTO 93",
    "RCL 04", "125", "X=Y?", "GTO 94",
    "RCL 04", "128", "X=Y?", "GTO 95",
    "RCL 04", "191", "X=Y?", "GTO 96",
    "RCL 04", "195", "X=Y?", "GTO 97",
    "RCL 04", "198", "X=Y?", "GTO 98",
    "RTN",
    "LBL 93", "2", "GTO 99",
    "LBL 94", "1", "XEQ 99", "2", "GTO 99",
    "LBL 95", "1", "GTO 99",
    "LBL 96", "8", "GTO 99",
    "LBL 97", "4", "XEQ 99", "8", "GTO 99",
    "LBL 98", "4",
    "LBL 99",
    "STO 03",
    "RCL 08", "RCL 03", "÷", "IP", "2", "MOD", "X=0?", "RTN",
    "RCL 03", "STO- 08",
    "RTN",
    # ---- unmake
    'LBL "ChUNMK"',
    "RCL 05", "+/-", "STO 05",
    "RCL 24", "STO IND 22",
    "XEQ 81", "STO 13", "RCL 22", "STO IND 13",
    "RCL 29", "1", "X=Y?", "GTO 65",
    "RCL 25", "STO IND 23",
    "X=0?", "GTO 66",
    "XEQ 81", "STO 13", "RCL 23", "STO IND 13",
    "LBL 66",
    "RCL 29", "2", "X=Y?", "GTO 67",
    "LBL 68",
    "RCL 24", "ABS", "IP", "6", "X≠Y?", "GTO 69",
    "19", "RCL 05", "-", "2", "÷", "STO 13", "RCL 22", "STO IND 13",
    "LBL 69",
    "RCL 28", "STO 06", "RCL 26", "STO 07", "RCL 27", "STO 08",
    "RTN",
    "LBL 65",
    "0", "STO IND 23",
    "RCL 05", "10", "×", "RCL 23", "X<>Y", "-", "STO 39",
    "RCL 25", "STO IND 39",
    "XEQ 81", "STO 13", "RCL 39", "STO IND 13",
    "GTO 69",
    "LBL 67",
    "RCL 23", "RCL 22", "X<Y?", "GTO 70",
    "RCL 22", "1", "-", "STO 03", "RCL 22", "4", "-",
    "GTO 71",
    "LBL 70",
    "RCL 22", "1", "+", "STO 03", "RCL 22", "3", "+",
    "LBL 71",
    "STO 39",
    "RCL IND 03", "STO IND 39",
    "XEQ 81", "STO 13", "RCL 39", "STO IND 13",
    "0", "STO IND 03",
    "GTO 68",
    # ---- piece-square value: R00 piece, R01 square -> X (signed, White's view)
    'LBL "ChPST"',
    "RCL 01", "880", "+", "RCL IND ST X", "STO 02",
    "RCL 00", "ABS", "IP", "STO 03",
    "1", "X=Y?", "GTO 76",
    "RCL 03", "75", "+", "STO 04",
    "RCL IND 04", "RCL 02", "×", "STO 02",
    "RCL 03", "69", "+", "STO 04",
    "RCL IND 04", "RCL 02", "+",
    "GTO 77",
    "LBL 76",
    "RCL 01", "10", "÷", "IP", "15.5", "-",
    "RCL 00", "SIGN", "×", "2.5", "+", "STO 04",
    "RCL 02", "×",
    "RCL 04", "X↑2", "2", "×", "+",
    "100", "+",
    "LBL 77",
    "RCL 00", "SIGN", "×",
    "RTN",
    # ---- recompute score from scratch
    'LBL "ChRESC"',
    "0", "STO 06",
    "1081", "STO 12",
    "LBL 78",
    "RCL IND 12", "X=0?", "GTO 79",
    "STO 01", "RCL IND ST X", "STO 00",
    'XEQ "ChPST"', "STO+ 06",
    "LBL 79",
    "1", "STO+ 12", "RCL 12", "1113", "X≠Y?", "GTO 78",
    "RTN",
    "END",
)



def split_strings(lines):
    out = []
    for line in lines:
        m = re.fullmatch(r'(├?)"(.*)"', line)
        if not m:
            out.append(line); continue
        app, body = m.groups()
        toks = re.findall(r'\[LF\]|.', body)
        first = True
        while toks:
            is_app = app or not first
            n = 14 if is_app else 15
            chunk, toks = toks[:n], toks[n:]
            out.append(('├' if is_app else '') + '"' + ''.join(chunk) + '"')
            first = False
    return out


def listing(numbered=True):
    out = []
    n = 0
    for line in ALL:
        if line.startswith("LBL \""):
            n = 0
        n += 1
        if numbered:
            pre = f"{n:02d}{'▸' if line.startswith('LBL') else ' '}"
            out.append(pre + line)
        else:
            out.append(line)
    return out


ALL = split_strings(chess + cinit + srch + gen + make)

if __name__ == "__main__":
    import sys
    open(sys.argv[1] if len(sys.argv) > 1 else "chess42.txt", "w").write(
        "\n".join(listing(False)) + "\n")

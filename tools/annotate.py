#!/usr/bin/env python3
"""Write the commented program listing (comments start with ').

The comments are for reading only; sim42.parse() and the encoder ignore them."""
import re
import sys
import gen3
from sim42 import encode

COL = 26  # column where comments start

REG = {
    0: "temp / PST piece", 1: "temp / PST square", 2: "temp", 3: "temp / pointer", 4: "temp",
    5: "side to move (+1 White, -1 Black)", 6: "score, White's view", 7: "en-passant square",
    8: "castling rights (1 WK, 2 WQ, 4 BK, 8 BQ)", 9: "white king square", 10: "black king square",
    11: "ply (search depth so far)", 12: "pointer", 13: "temp / sprite code / capture key",
    14: "alpha", 15: "beta", 16: "best score at this node", 17: "remaining depth",
    18: "move-list index", 19: "end of captures in list", 20: "start of quiet moves in list",
    21: "current move (from*1000+to)", 22: "move: from square", 23: "move: to square",
    24: "move: moving piece", 25: "move: captured piece", 26: "undo: old en-passant square",
    27: "undo: old castling rights", 28: "undo: old score", 29: "move type (1 e.p., 2 castle)",
    30: "move-list base for this ply", 31: "best root move", 32: "root score", 33: "level (search depth)",
    34: "ray direction (attack test)", 35: "value returned to parent", 36: "node counter",
    38: "engine service code", 39: "temp square",
    40: "direction +1", 41: "direction -1", 42: "direction +10", 43: "direction -10",
    44: "direction +9", 45: "direction -9", 46: "direction +11", 47: "direction -11",
    48: "end of direction list (0)", 49: "UI stage (0 pick piece, 1 pick target)",
    50: "UI selected piece square", 51: "draw row (y)", 52: "draw column (x)",
    53: "UI status message number", 54: "last move (for marks/panel)", 55: "key code",
    56: "movegen: from square", 57: "movegen: direction pointer", 59: "movegen: target square",
    60: "movegen: direction", 61: "movegen: piece-list pointer", 62: "movegen: piece-list end",
    63: "attack test: square", 64: "attack test: attacking side", 65: "attack test: direction pointer",
    66: "attack test: walking square", 67: "attack test: direction end", 68: "pawn step (+10/-10)",
    69: "attack test: piece type sought", 70: "value pawn", 71: "value knight", 72: "value bishop",
    73: "value rook", 74: "value queen", 75: "value king", 76: "centre weight pawn",
    77: "centre weight knight", 78: "centre weight bishop", 79: "centre weight rook",
    80: "centre weight queen", 81: "centre weight king", 82: "movegen: moving piece type",
    83: "UI cursor square", 84: "draw loop: rank", 85: "draw loop: file",
    86: "knight jump +8", 87: "knight jump -8", 88: "knight jump +12", 89: "knight jump -12",
    90: "knight jump +19", 91: "knight jump -19", 92: "knight jump +21", 93: "knight jump -21",
    94: "end of knight list (0)", 95: "rook direction +1", 96: "rook direction -1",
    97: "rook direction +10", 98: "rook direction -10", 99: "end of rook list (0)",
}
FLAG = {1: "quiescence (captures only)", 2: "king can be captured", 3: "square attacked / in check",
        5: "side to move has a legal move", 6: "engine service call", 7: "first run: build tables"}
SVC_NAME = {v: k for k, v in gen3.SVC.items()}

DOC = {
    # entry points
    '"CHESS"': "new game, or engine service if flag 06 set",
    '"CHCON"': "graphical UI: continue game",
    "@SVC": "engine service dispatcher (code in R38)",
    "@ChCINIT": "set up constant tables", "@ChSETUP": "set up start position",
    "@ChSRCH": "alpha-beta search from the root", "@ChSPILL": "save node record for this ply",
    "@ChRESTO": "restore node record for this ply", "@ChINCHK": "flag 03 if side to move in check",
    "@ChMCHK": "flag 03 if mover's king is attacked", "@ChGEN0": "generate moves at ply 0",
    "@ChHASMV": "flag 05 if side to move has a legal move", "@ChGEN": "generate pseudo-legal moves",
    "@ChATT": "flag 03 if square R63 attacked by side R64", "@ChMAKE": "make move R21",
    "@ChUNMK": "undo last move", "@ChPST": "piece-square value of R00 on R01",
    "@ChRESC": "recompute score from scratch",
    # setup
    "@ci_15": "centre table: rank loop", "@ci_16": "centre table: file loop",
    "@ci_17": "mark all squares off-board", "@ci_18": "clear board: rank loop",
    "@ci_19": "clear board: file loop", "@ci_20": "place pieces, file by file",
    # search
    "@se_30": "enter node", "@se_31": "full-width node", "@se_32": "return value to parent",
    "@se_33": "generate moves for node", "@se_34": "king capturable: last move illegal",
    "@se_35": "next move", "@se_36": "end of move list?", "@se_37": "node finished",
    "@se_38": "new best move", "@se_39": "raise alpha, test cutoff", "@se_40": "make move, go one ply deeper",
    "@se_41": "losing-looking capture?", "@se_42": "skip it if target is defended",
    "@se_15": "next move", "@se_16": "end of move list?",
    # move generation
    "@ge_40": "next piece in piece list", "@ge_33": "pawn or knight", "@ge_34": "bishop",
    "@ge_35": "rook", "@ge_36": "queen", "@ge_37": "pawn", "@ge_30": "piece done",
    "@ge_41": "pawn moves", "@ge_57": "pawn captures", "@ge_59": "pawn capture towards square X",
    "@ge_48": "en-passant capture", "@ge_58": "pawn push (promotion to capture list)",
    "@ge_62": "promotion", "@ge_42": "knight moves", "@ge_43": "bishop moves", "@ge_44": "rook moves",
    "@ge_45": "queen moves", "@ge_46": "king moves", "@ge_47": "add quiet move",
    "@ge_49": "add capture, sorted MVV/LVA", "@ge_63": "insertion-sort step", "@ge_64": "store capture",
    "@ge_50": "occupied target: capture?", "@ge_53": "slider: next direction",
    "@ge_55": "slider: next square on ray", "@ge_54": "slider: ray blocked",
    "@ge_56": "stepper: next direction", "@ge_52": "stepper: empty square",
    "@ge_60": "castling, king side", "@ge_61": "castling, queen side",
    "@ge_71": "attacker of wanted type on square X?", "@ge_72": "knight/king attackers",
    "@ge_74": "slider attackers: next direction", "@ge_75": "slider attackers: walk ray",
    # make / unmake / evaluation
    "@ma_80": "capture handled", "@ma_82": "not a pawn: king?", "@ma_83": "not en passant",
    "@ma_84": "not a double push", "@ma_85": "promotion to queen", "@ma_86": "normal piece",
    "@ma_87": "put piece on target square", "@ma_88": "switch side to move",
    "@ma_81": "piece value -> piece-list register", "@ma_89": "castling rights for square X",
    "@ma_72": "corner or king square?", "@ma_93": "a1: lose WQ", "@ma_94": "e1: lose WK+WQ",
    "@ma_95": "h1: lose WK", "@ma_96": "a8: lose BQ", "@ma_97": "e8: lose BK+BQ", "@ma_98": "h8: lose BK",
    "@ma_99": "clear castling bit X", "@ma_90": "castle king side: rook", "@ma_91": "castle queen side: rook",
    "@ma_92": "move the rook", "@ma_65": "undo en passant", "@ma_66": "captured piece restored",
    "@ma_67": "undo castling rook", "@ma_68": "restore king square", "@ma_69": "restore score, e.p., rights",
    "@ma_70": "king side rook back", "@ma_71": "put rook back", "@ma_76": "pawn value",
    "@ma_77": "apply colour sign", "@ma_78": "next piece", "@ma_79": "piece captured: skip",
    # UI
    "@UINIT": "build glyph tables", "@REDRAW": "redraw screen, then wait for key",
    "@KEY": "wait for a key", "@UP": "8: cursor up", "@DOWN": "2: cursor down", "@LEFT": "4: cursor left",
    "@RIGHT": "6: cursor right", "@MOVE": "move cursor if it stays on board", "@ENTER": "ENTER pressed",
    "@NOTOWN": "not your piece", "@DEST": "target chosen: try the move", "@SCAN": "search move list",
    "@SCAN2": "end of list?", "@FOUND": "move found: make it", "@ILLEGAL": "illegal move",
    "@LEGAL": "legal: computer replies", "@LEVEL": "9: next level", "@CLEAR": "<-: clear selection",
    "@QUIT": "EXIT: back to normal display", "@ENGINE": "computer's move", "@SETCHK": "status: check",
    "@SETEND": "status: game over", "@SETMATE": "status: I win", "@NOMOVE": "computer has no move",
    "@SETWIN": "status: you win", "@DRAW": "draw whole screen", "@DR1": "board: rank loop",
    "@DR2": "board: file loop", "@DR3": "cursor frame", "@DR4": "board border",
    "@BRD1": "horizontal border lines", "@BRD2": "vertical border lines", "@CRD": "coordinates a-h, 1-8",
    "@PN1": "panel: move line", "@PN2": "panel: cursor square", "@SQXY": "square R39 -> row R51, col R52",
    "@SQB": "big text: square name X", "@BIG1": "big text: one character", "@SPR": "draw sprite R13",
}
for k, m in gen3.MSGS.items():
    DOC[f"@MSG{k}"] = f'status text "{m}"'
for c in gen3.sp:
    if c >= 26:
        DOC[f"@S{c}"] = {26: "sprite: cursor frame", 27: "sprite: last-move corners",
                         28: "sprite: selected piece"}[c]
    elif c == 13:
        DOC[f"@S{c}"] = "sprite: empty dark square"
    else:
        DOC[f"@S{c}"] = ("sprite: " + ("white " if c > 13 else "black ") + "PNBRQK"[abs(c // 2 - 6) - 1]
                         + (" on dark" if c % 2 else " on light"))


def comment_for(sym, prev):
    m = re.fullmatch(r'LBL (@\S+|"\w+")', sym)
    if m:
        name = m.group(1)
        if name.startswith("@T"):
            return "sprite search tree"
        return DOC.get(name, "")
    m = re.fullmatch(r'(GTO|XEQ) (@\S+)', sym)
    if m:
        name = m.group(2)
        if name.startswith("@T"):
            return "-> sprite search tree"
        d = DOC.get(name, "")
        return ("-> " + d) if d else ""
    if sym == 'XEQ "CHESS"' and prev:
        return "engine: " + DOC.get("@" + SVC_NAME.get(prev, ""), "")
    if sym == 'GTO "CHCON"':
        return "start the UI"
    m = re.fullmatch(r'(RCL|STO|STO\+|STO-|STO×|STO÷|X<>|ASTO|ARCL) (\d\d)', sym)
    if m:
        return REG.get(int(m.group(2)), "")
    m = re.fullmatch(r'(SF|CF|FS\?|FC\?|FS\?C|FC\?C) (\d\d)', sym)
    if m:
        return "flag: " + FLAG.get(int(m.group(2)), "")
    if sym == 'STO "GrMod"':
        return "graphics mode (3 = 400x240)"
    if sym == "GETKEY":
        return "wait for a key"
    if sym == "AGRAPH":
        return "draw ALPHA as pixels at row Y, col X"
    if sym.startswith("SIZE"):
        return "allocate registers"
    return ""


def commented(prog_sym, prog_final):
    out = []
    prev_svc = None
    for i, (sym, fin) in enumerate(zip(prog_sym, prog_final)):
        if sym == "SF 06" and i + 1 < len(prog_sym):
            prev_svc = int(prog_sym[i + 1])
        c = comment_for(sym, prev_svc if sym == 'XEQ "CHESS"' else None)
        out.append(fin.ljust(COL) + "'" + c if c else fin)
    return out


def numbered(lines, prog):
    """Free42-style numbering: 0000 { n-Byte Prgm }, then 0001, 0002, ...
    n = encoded size of the program without its END."""
    size = len(encode("\n".join(prog))) - len(encode("END"))
    return [f"0000 {{ {size}-Byte Prgm }}"] + [f"{i:04d} {l}" for i, l in enumerate(lines, 1)]


HEADER = [
    "' RPN Chess42 for the SwissMicros DM42 - commented listing",
    "' Two programs: CHESS (engine, new game) and CHCON (graphical UI).",
    "' Board: R100-R219 (10x12 mailbox, a1 = R121, h8 = R198); piece = side*(type + k/100)",
    "'   type P1 N2 B3 R4 Q5 K6, k = piece-list slot (R1081-R1112), off-board = 0.5",
    "' Node records R220-R355, move lists R360-R999, centre table R1001-R1078,",
    "' small glyphs R1141-R1158, large glyphs R1160-R1223.",
    "' Strings with picture data use [xHH] for byte HH. Load CHESS.raw rather than this text.",
    "",
]

if __name__ == "__main__":
    lines = HEADER + numbered(commented(gen3.engine, gen3.ENG), gen3.ENG) + [""] \
        + numbered(commented(gen3.ui, gen3.UI), gen3.UI)
    open(sys.argv[1] if len(sys.argv) > 1 else "../CHESS_listing.txt", "w").write("\n".join(lines) + "\n")

import chess, random
from decimal import Decimal as D
from sim42 import *

TYPE = {chess.PAWN:1, chess.KNIGHT:2, chess.BISHOP:3, chess.ROOK:4, chess.QUEEN:5, chess.KING:6}

def sq42(s): return 110 + 10*(s//8+1) + (s%8+1)
def sqpc(q): return (q//10 - 11 - 1)*8 + (q%10 - 1)

SVCODE = {"ChGEN0": 1, "ChMAKE": 2, "ChMCHK": 3, "ChUNMK": 4, "ChSRCH": 5, "ChHASMV": 6, "ChINCHK": 7, "ChRESC": 8}
def svc(c, name):
    c.flags[6] = True; c.regs[38] = D(SVCODE[name]); c.xeq('CHESS')

def new_calc():
    import os
    c = Calc(open(os.environ.get('PRG','chess3.txt')).read())
    c.xeq('CHESS')
    return c

def load(c, b):
    R = c.regs
    for i in range(100, 220): R[i] = D('0.5')
    for r in range(1,9):
        for f in range(1,9): R[110+10*r+f] = D(0)
    for k in range(1081, 1113): R[k] = D(0)
    kw, kb = 1, 17
    for s, p in b.piece_map().items():
        if p.color: k = kw; kw += 1
        else: k = kb; kb += 1
        v = D(TYPE[p.piece_type]) + D(k)/100
        R[sq42(s)] = v if p.color else -v
        R[1080+k] = D(sq42(s))
    R[5] = D(1 if b.turn else -1)
    R[7] = D(sq42(b.ep_square)) if b.ep_square is not None else D(0)
    cr = 0
    if b.castling_rights & chess.BB_H1: cr |= 1
    if b.castling_rights & chess.BB_A1: cr |= 2
    if b.castling_rights & chess.BB_H8: cr |= 4
    if b.castling_rights & chess.BB_A8: cr |= 8
    R[8] = D(cr)
    R[9] = D(sq42(b.king(chess.WHITE))); R[10] = D(sq42(b.king(chess.BLACK)))
    svc(c,'ChRESC')

def m2uci(m):
    m = int(m); f, t = m//1000, m%1000
    return chess.square_name(sqpc(f)) + chess.square_name(sqpc(t))

def gen_list(c):
    svc(c,'ChGEN0')
    R = c.regs; lb = int(R[30]); ce = int(R[19]); qs = int(R[20])
    return [R[i] % 1000000 for i in range(lb, ce)] + [R[i] % 1000000 for i in range(qs, lb+80)]

def legal42(c):
    out = []
    for m in gen_list(c):
        snap = list(c.regs[:1113])
        c.regs[21] = m
        svc(c,'ChMAKE'); svc(c,'ChMCHK')
        ok = not c.flags[3]
        svc(c,'ChUNMK')
        for i in range(1113):
            if i in (38,0,1,2,3,4,13,21,22,23,24,25,26,27,28,29,39,63,64,65,66,67,69,34): continue
            if c.regs[i] != snap[i]:
                raise AssertionError(f'unmake mismatch R{i} {snap[i]} -> {c.regs[i]} move {m2uci(m)}')
        if ok: out.append(m2uci(m))
    return out

def legal_pc(b):
    s = set()
    for m in b.legal_moves:
        if m.promotion and m.promotion != chess.QUEEN: continue
        s.add(m.uci()[:4])
    return s

def check_score(c, b):
    # recompute score from scratch and compare to incremental
    inc = c.regs[6]; svc(c,'ChRESC'); assert c.regs[6] == inc, (inc, c.regs[6])

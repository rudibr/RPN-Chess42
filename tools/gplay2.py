import chess, random, sys
from sim42 import *
random.seed(int(sys.argv[1])); level=int(sys.argv[2])
UP,DOWN,LEFT,RIGHT,ENTER,BACK,EXIT=20,30,24,26,13,17,33
c = Calc(open('chess3.txt').read()); c.xeq('CHESS')
steps=[]
def press(*ks):
    for k in ks:
        c.keys.append(k); s0=c.steps; r=c.cont(); steps.append((k,c.steps-s0)); assert r=='GETKEY', r
def goto(u):
    f,r = ord(u[0])-96, int(u[1])
    cur=int(c.regs[83]); cf,cr=cur%10, cur//10-11
    press(*([RIGHT]*(f-cf) if f>cf else [LEFT]*(cf-f)), *([UP]*(r-cr) if r>cr else [DOWN]*(cr-r)))
    assert int(c.regs[83])==110+10*r+f, (u, c.regs[83])
def m2u(m):
    m=int(m); f,t=m//1000,m%1000
    return "abcdefgh"[f%10-1]+str(f//10-11)+"abcdefgh"[t%10-1]+str(t//10-11)
while int(c.regs[33])!=level: press(21)
# edge test: cursor can't leave board
goto('a1'); press(LEFT, DOWN); assert int(c.regs[83])==121
goto('e2'); press(ENTER); goto('e4'); screenshot(c,'c_sel.png'); press(BACK); assert c.regs[49]==0
goto('e5'); press(ENTER); assert c.regs[53]==8
b=chess.Board(); n=0
while not b.is_game_over() and n<60:
    legal=[m for m in b.legal_moves if not m.promotion or m.promotion==chess.QUEEN]
    if n==1:  # illegal attempt
        mv0=next(m for m in legal)
        goto(mv0.uci()[:2]); press(ENTER); goto('h8' if mv0.uci()[:2]!='h8' else 'a8')
        press(ENTER); assert c.regs[53] in (3,), c.regs[53]
    mv=random.choice(legal); b.push(mv); u=mv.uci()
    goto(u[:2]); press(ENTER); goto(u[2:4]); press(ENTER); n+=1
    msg=int(c.regs[53])
    if c.regs[31]==0 and msg in (6,7): print("you ended it", msg, b.is_checkmate(), b.is_stalemate()); break
    em=chess.Move.from_uci(m2u(c.regs[54]))
    if b.piece_at(em.from_square).piece_type==chess.PAWN and chess.square_rank(em.to_square) in (0,7): em.promotion=chess.QUEEN
    assert em in b.legal_moves, (em,b.fen()); b.push(em)
    if msg in (5,7): print("engine:", msg, b.is_checkmate(), b.is_stalemate()); break
    if msg==4: assert b.is_check()
print("moves",n)
cur=[s for k,s in steps if k in (UP,DOWN,LEFT,RIGHT)]
print("cursor key steps avg", sum(cur)//len(cur), "max", max(cur))
screenshot(c,'c_end.png')

from harness import *
import sys
random.seed(int(sys.argv[1]))
c = new_calc()
def state(c):
    R=c.regs
    bd = tuple(int(R[i].to_integral_value(rounding='ROUND_DOWN')) if abs(R[i])>=1 else 0 for i in range(100,220))
    # PL consistency
    for k in range(1081,1113):
        if R[k]!=0:
            v=R[int(R[k])]; assert abs(v)>=1 and int((abs(v)%1)*100+D('0.5'))==k-1080, ('PL',k)
    return bd, R[5], R[7], R[8], R[9], R[10], R[6]
games=0; plies=0
for g in range(15):
    b = chess.Board(); load(c, b)
    for ply in range(150):
        legal = [m for m in b.legal_moves if not m.promotion or m.promotion==chess.QUEEN]
        if not legal: break
        mv = random.choice(legal)
        # find calc move
        ms = {m2uci(m): m for m in gen_list(c)}
        c.regs[21] = ms[mv.uci()[:4]]
        svc(c,'ChMAKE'); b.push(mv); plies+=1
        s1 = state(c)
        c2 = c  # compare with fresh load into a copy
        saved = list(c.regs)
        load(c, b); s2 = state(c)
        if s1[:6] != s2[:6] or s1[6]!=s2[6]:
            print("DIFF", b.fen(), s1[1:], s2[1:]); sys.exit(1)
        c.regs = saved
    games+=1
print("ok games", games, "plies", plies)

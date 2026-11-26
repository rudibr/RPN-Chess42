#!/usr/bin/env python3
"""Record a game in the simulator as an animated GIF (400x240, native DM42 resolution).
White's moves are chosen by a second copy of the engine and entered with the cursor keys."""
import os, sys
os.environ.setdefault('PRG', 'chess3.txt')
import chess
from PIL import Image
from harness import load, svc, m2uci
from sim42 import Calc
from decimal import Decimal as D

UP, DOWN, LEFT, RIGHT, ENTER = 20, 30, 24, 26, 13
TEXT = open('chess3.txt').read()
ui = Calc(TEXT); helper = Calc(TEXT)
frames, durations = [], []

def snap(ms):
    im = Image.new('1', (400, 240), 1)
    px = im.load()
    for y in range(240):
        row = ui.fb[y]
        for x in range(400):
            if row[x]:
                px[x, y] = 0
    frames.append(im); durations.append(ms)

orig = ui.exec
def ex(ins):
    if ins[0] == 'XEQ' and ins[1] == ('G', 'CHESS') and ui.flags[6] and ui.regs[38] == 5:
        snap(900)                      # "Thinking..." screen
    return orig(ins)
ui.exec = ex

def press(k, ms):
    ui.keys.append(k); r = ui.cont(); assert r == 'GETKEY', r; snap(ms)

def goto(sq):
    f, r = ord(sq[0]) - 96, int(sq[1])
    cur = int(ui.regs[83]); cf, cr = cur % 10, cur // 10 - 11
    for k in ([RIGHT] * (f - cf) if f > cf else [LEFT] * (cf - f)) + \
             ([UP] * (r - cr) if r > cr else [DOWN] * (cr - r)):
        press(k, 120)

ui.xeq('CHESS'); snap(1500)
helper.xeq('CHESS'); helper.regs[33] = D(2)
board = chess.Board()
nmoves = int(sys.argv[1]) if len(sys.argv) > 1 else 12
for i in range(nmoves):
    load(helper, board); svc(helper, 'ChSRCH')
    u = m2uci(helper.regs[31])
    goto(u[:2]); press(ENTER, 400)
    goto(u[2:]); 
    press(ENTER, 1800)                 # engine reply shown
    board.push(chess.Move.from_uci(u + ('q' if board.piece_at(chess.parse_square(u[:2])).piece_type == 1 and u[3] in '18' else '')))
    if ui.regs[31] == 0: break
    em = m2uci(ui.regs[54])
    p = board.piece_at(chess.parse_square(em[:2]))
    board.push(chess.Move.from_uci(em + ('q' if p.piece_type == 1 and em[3] in '18' else '')))
    if board.is_game_over(): break
durations[-1] = 4000
frames[0].save('../demo.gif', save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
print(len(frames), 'frames', os.path.getsize('../demo.gif'), 'bytes', board.fen())

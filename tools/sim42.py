#!/usr/bin/env python3
"""Minimal HP-42S/Free42 simulator for the instruction subset used by chess42,
plus a .raw encoder.  Arithmetic uses 34-digit decimal like the DM42."""
import re
from decimal import Decimal as D, getcontext, ROUND_DOWN

getcontext().prec = 34


class Stop(Exception):
    pass


class CalcError(Exception):
    pass


def tokenize_string(body):
    return re.findall(r'\[LF\]|\[x[0-9A-F]{2}\]|.', body)


def chars(body):
    out = ''
    for t in tokenize_string(body):
        if t == '[LF]':
            out += '\n'
        elif t.startswith('[x'):
            out += chr(int(t[2:4], 16))
        else:
            out += t
    return out


STACKREF = {'ST T': 0x70, 'ST Z': 0x71, 'ST Y': 0x72, 'ST X': 0x73, 'ST L': 0x74}


def strip_comment(raw):
    """Remove a trailing ' comment (and whole-line comments). Quotes inside strings are kept."""
    s = raw.strip()
    if s.startswith("'"):
        return ''
    in_str = False
    for i, ch in enumerate(s):
        if ch == '"':
            in_str = not in_str
        elif ch == "'" and not in_str:
            return s[:i].strip()
    return s


def parse(text):
    progs = []
    cur = []
    for raw in text.splitlines():
        line = strip_comment(raw)
        line = re.sub(r'^\d+[▸ ]', '', line).strip()
        if not line or line.startswith('{'):
            continue
        cur.append(line)
        if line == 'END':
            progs.append(cur)
            cur = []
    if cur:
        progs.append(cur)
    return progs


class Calc:
    def __init__(self, text):
        self.progs = parse(text)
        self.labels = {}      # (prog, label) -> idx
        self.globals = {}
        self.code = []
        for p, lines in enumerate(self.progs):
            ins = []
            for i, l in enumerate(lines):
                ins.append(self.decode(l))
                m = re.fullmatch(r'LBL "(.+)"', l)
                if m:
                    if m.group(1) in self.globals:
                        raise ValueError('dup global ' + m.group(1))
                    self.globals[m.group(1)] = (p, i)
                m = re.fullmatch(r'LBL (\d\d|[A-Ja-e])', l)
                if m:
                    k = (p, m.group(1))
                    if k in self.labels:
                        raise ValueError(f'dup label {k}')
                    self.labels[k] = i
            self.code.append(ins)
        self.regs = [D(0)] * 25
        self.X = self.Y = self.Z = self.T = self.L = D(0)
        self.lift = True
        self.flags = [False] * 100
        self.alpha = ''
        self.fix = None
        self.steps = 0
        self.rtn = []
        self.pc = None
        self.display = []
        self.named = {}
        self.fb = [[0] * 400 for _ in range(240)]
        self.keys = []

    # ---------- decode ----------
    def decode(self, l):
        if re.fullmatch(r'-?[\d.]+', l):
            return ('NUM', D(l))
        m = re.fullmatch(r'(├?)"(.*)"', l)
        if m:
            return ('STR', bool(m.group(1)), chars(m.group(2)))
        parts = l.split(' ', 1)
        op = parts[0]
        arg = parts[1] if len(parts) > 1 else None
        if op in ('LBL', 'GTO', 'XEQ') and arg and re.fullmatch(r'\d\d|[A-Ja-e]', arg):
            return (op, ('L', arg))
        if arg is not None:
            if arg.startswith('"'):
                arg = ('G', arg.strip('"'))
            elif arg.startswith('IND '):
                a = arg[4:]
                arg = ('IND', ('S', a) if a in STACKREF else ('R', int(a)))
            elif arg in STACKREF:
                arg = ('S', arg)
            else:
                arg = ('R', int(arg))
        return (op, arg)

    # ---------- stack ----------
    def push(self, v):
        if self.lift:
            self.T, self.Z, self.Y = self.Z, self.Y, self.X
        self.X = v
        self.lift = True

    def drop(self, v):
        self.L = self.X
        self.X, self.Y, self.Z = v, self.Z, self.T

    def getstack(self, s):
        return {'ST X': self.X, 'ST Y': self.Y, 'ST Z': self.Z, 'ST T': self.T, 'ST L': self.L}[s]

    def setstack(self, s, v):
        setattr(self, {'ST X': 'X', 'ST Y': 'Y', 'ST Z': 'Z', 'ST T': 'T', 'ST L': 'L'}[s], v)

    def regnum(self, v):
        if isinstance(v, str):
            raise CalcError('IND on string')
        if v != v.to_integral_value() or v < 0:
            raise CalcError(f'bad IND {v}')
        n = int(v)
        if n >= len(self.regs):
            raise CalcError(f'Nonexistent R{n}')
        return n

    def resolve(self, arg):
        """returns ('R', n) or ('S', name)"""
        kind, a = arg
        if kind == 'IND':
            v = self.regs[self.regnum_direct(a[1])] if a[0] == 'R' else self.getstack(a[1])
            return ('R', self.regnum(v))
        if kind == 'R':
            return ('R', self.regnum_direct(a))
        return arg

    def regnum_direct(self, n):
        if n >= len(self.regs):
            raise CalcError(f'Nonexistent R{n}')
        return n

    def get(self, arg):
        if arg[0] == 'G':
            return self.named[arg[1]]
        k, a = self.resolve(arg)
        return self.regs[a] if k == 'R' else self.getstack(a)

    def put(self, arg, v):
        if arg[0] == 'G':
            self.named[arg[1]] = v
            return
        k, a = self.resolve(arg)
        if k == 'R':
            self.regs[a] = v
        else:
            self.setstack(a, v)

    def fmt(self, v):
        if isinstance(v, str):
            return v
        if self.fix is not None:
            q = D(1).scaleb(-self.fix)
            s = str(v.quantize(q))
            if s.startswith('-') and float(s) == 0:
                s = s[1:]
            return s
        return str(v.normalize())

    # ---------- run ----------
    def xeq(self, name, max_steps=10**9):
        self.rtn = []
        self.pc = list(self.globals[name])
        return self.run(max_steps)

    def run(self, max_steps=10**9):
        start = self.steps
        while True:
            if self.steps - start > max_steps:
                raise CalcError('step limit')
            p, i = self.pc
            ins = self.code[p][i]
            self.pc[1] += 1
            self.steps += 1
            r = self.exec(ins)
            if r is not None:
                return r

    def skip(self):
        self.pc[1] += 1

    def jump_local(self, n):
        p = self.pc[0]
        if (p, n) not in self.labels:
            raise CalcError(f'no label {n} in prog {p}')
        self.pc = [p, self.labels[(p, n)]]

    def exec(self, ins):
        op = ins[0]
        a = ins[1] if len(ins) > 1 else None
        if op == 'NUM':
            self.push(a)
            return
        if op == 'STR':
            app, s = ins[1], ins[2]
            self.alpha = (self.alpha + s if app else s)[-44:]
            return
        X, Y = self.X, self.Y
        if op in ('+', '-', '×', '÷', 'MOD'):
            if isinstance(X, str) or isinstance(Y, str):
                raise CalcError('alpha data')
            if op == '+': v = Y + X
            elif op == '-': v = Y - X
            elif op == '×': v = Y * X
            elif op == '÷':
                if X == 0: raise CalcError('Divide by 0')
                v = Y / X
            else:
                if X == 0: v = Y
                else:
                    v = Y - X * (Y / X).to_integral_value(rounding='ROUND_FLOOR')
            self.drop(v); self.lift = True; return
        if op in ('ABS', 'IP', 'FP', 'SIGN', '+/-', 'X↑2'):
            if op == 'ABS': v = abs(X)
            elif op == 'IP': v = X.to_integral_value(rounding=ROUND_DOWN)
            elif op == 'FP': v = X - X.to_integral_value(rounding=ROUND_DOWN)
            elif op == 'SIGN': v = D((X > 0) - (X < 0))
            elif op == '+/-': v = -X
            else: v = X * X
            if op not in ('+/-',):
                self.L = X
            self.X = v; self.lift = True; return
        if op == 'ENTER':
            self.T, self.Z, self.Y = self.Z, self.Y, self.X; self.lift = False; return
        if op == 'CLX':
            self.X = D(0); self.lift = False; return
        if op == 'X<>Y':
            self.X, self.Y = Y, X; self.lift = True; return
        if op == 'R↓':
            self.X, self.Y, self.Z, self.T = self.Y, self.Z, self.T, self.X; self.lift = True; return
        if op == 'R↑':
            self.X, self.Y, self.Z, self.T = self.T, self.X, self.Y, self.Z; self.lift = True; return
        if op == 'LASTX':
            self.push(self.L); return
        if op == 'RCL':
            self.push(self.get(a)); return
        if op == 'STO':
            self.put(a, X); self.lift = True; return
        if op in ('STO+', 'STO-', 'STO×', 'STO÷'):
            v = self.get(a)
            v = {'STO+': v + X, 'STO-': v - X, 'STO×': v * X, 'STO÷': (v / X if X else None)}[op]
            self.put(a, v); self.lift = True; return
        if op == 'X<>':
            v = self.get(a); self.put(a, X); self.X = v; self.lift = True; return
        tests = {'X=Y?': lambda: X == Y, 'X≠Y?': lambda: X != Y, 'X<Y?': lambda: X < Y,
                 'X>Y?': lambda: X > Y, 'X≤Y?': lambda: X <= Y, 'X=0?': lambda: X == 0,
                 'X≠0?': lambda: X != 0, 'X<0?': lambda: X < 0, 'X>0?': lambda: X > 0,
                 'X≤0?': lambda: X <= 0}
        if op in tests:
            if isinstance(X, str) or isinstance(Y, str) and op in ('X<Y?', 'X>Y?', 'X≤Y?'):
                raise CalcError('alpha compare')
            if not tests[op]():
                self.skip()
            self.lift = True
            return
        if op == 'FS?C':
            n = a[1]
            v = self.flags[n]; self.flags[n] = False
            if not v: self.skip()
            return
        if op in ('SF', 'CF', 'FS?', 'FC?'):
            n = a[1]
            if op == 'SF': self.flags[n] = True
            elif op == 'CF': self.flags[n] = False
            elif op == 'FS?':
                if not self.flags[n]: self.skip()
            else:
                if self.flags[n]: self.skip()
            return
        if op in ('GTO', 'XEQ'):
            if op == 'XEQ':
                self.rtn.append(list(self.pc))
            if a[0] == 'G':
                self.pc = list(self.globals[a[1]])
            elif a[0] == 'L':
                self.jump_local(a[1])
            elif a[0] == 'IND':
                inner = a[1]
                v = self.regs[inner[1]] if inner[0] == 'R' else self.getstack(inner[1])
                self.jump_local(int(v))
            else:
                raise CalcError('bad jump')
            return
        if op in ('RTN', 'END'):
            if self.rtn:
                self.pc = self.rtn.pop()
                return
            return 'RTN'
        if op == 'LBL':
            return
        if op == 'CLA':
            self.alpha = ''; return
        if op == 'ARCL':
            self.alpha = (self.alpha + self.fmt(self.get(a)))[-44:]; return
        if op == 'ASTO':
            self.put(a, self.alpha[:6]); return
        if op == 'AVIEW':
            self.display.append(self.alpha); return
        if op == 'PROMPT':
            self.display.append(self.alpha); return 'PROMPT'
        if op == 'STOP':
            return 'STOP'
        if op == 'GETKEY':
            if not self.keys:
                self.pc[1] -= 1
                self.steps -= 1
                return 'GETKEY'
            self.push(D(self.keys.pop(0)))
            return
        if op == 'CLLCD':
            self.fb = [[0] * 400 for _ in range(240)]
            return
        if op == 'AGRAPH':
            if self.named.get('GrMod') != D(3):
                raise CalcError('AGRAPH outside GrMod 3')
            col, row = int(X), int(Y)
            if len(self.alpha) > 44:
                raise CalcError('alpha too long')
            for i, ch in enumerate(self.alpha):
                b = ord(ch)
                for k in range(8):
                    if b >> k & 1:
                        y, x = row + k - 1, col + i - 1
                        if 0 <= y < 240 and 0 <= x < 400:
                            self.fb[y][x] = 1
                        else:
                            raise CalcError(f'pixel off screen {x},{y}')
            return
        if op == 'FIX':
            self.fix = a[1]; return
        if op == 'SIZE':
            n = a[1]
            self.regs = (self.regs + [D(0)] * n)[:n]
            return
        raise CalcError('unknown op ' + op)

    # harness helpers
    def key_number(self, v):
        """User types a number then presses R/S."""
        self.push(D(v))

    def cont(self, max_steps=10**9):
        return self.run(max_steps)


# ---------------- .raw encoder ----------------
SIMPLE = {
    '+': 0x40, '-': 0x41, '×': 0x42, '÷': 0x43, 'X<Y?': 0x44, 'X>Y?': 0x45, 'X≤Y?': 0x46,
    'MOD': 0x4B, 'X↑2': 0x51, '+/-': 0x54, 'ABS': 0x61, 'X≠0?': 0x63, 'X>0?': 0x64,
    'X<0?': 0x66, 'X=0?': 0x67, 'IP': 0x68, 'FP': 0x69, 'X<>Y': 0x71, 'R↑': 0x74,
    'R↓': 0x75, 'LASTX': 0x76, 'CLX': 0x77, 'X=Y?': 0x78, 'X≠Y?': 0x79, 'SIGN': 0x7A,
    'X≤0?': 0x7B, 'AVIEW': 0x7E, 'ENTER': 0x83, 'STOP': 0x84, 'RTN': 0x85, 'BEEP': 0x86,
    'CLA': 0x87, 'PROMPT': 0x8E,
}
TWOBYTE = {'GETKEY': b'\xA2\x6E', 'AGRAPH': b'\xA7\x64', 'CLLCD': b'\xA7\x63', 'PIXEL': b'\xA7\x65'}
REGOP = {'RCL': 0x90, 'STO': 0x91, 'STO+': 0x92, 'STO-': 0x93, 'STO×': 0x94, 'STO÷': 0x95,
         'ISG': 0x96, 'DSE': 0x97, 'VIEW': 0x98, 'ASTO': 0x9A, 'ARCL': 0x9B, 'FIX': 0x9C,
         'SF': 0xA8, 'CF': 0xA9, 'FS?C': 0xAA, 'FC?C': 0xAB, 'FS?': 0xAC, 'FC?': 0xAD,
         'X<>': 0xCE}


def charcode(c):
    if c == '\n':
        return 0x0A
    o = ord(c)
    if 0 <= o < 256:
        return o
    raise ValueError('char ' + repr(c))


def operand(arg):
    """arg like '05', 'IND 12', 'ST X', 'IND ST X' -> byte"""
    ind = 0
    if arg.startswith('IND '):
        ind = 0x80
        arg = arg[4:]
    if arg in STACKREF:
        return ind | STACKREF[arg]
    n = int(arg)
    assert 0 <= n <= 99, arg
    return ind | n


def labcode(arg):
    if arg in 'ABCDEFGHIJ' and len(arg) == 1:
        return 0x66 + 'ABCDEFGHIJ'.index(arg)
    if arg in 'abcde' and len(arg) == 1:
        return 0x7B + 'abcde'.index(arg)
    n = int(arg)
    assert 0 <= n <= 99
    return n


def encode_line(l):
    if re.fullmatch(r'-?[\d.]+', l):
        out = []
        for c in l:
            out.append({'.': 0x1A, '-': 0x1C}.get(c, 0x10 + int(c) if c.isdigit() else None))
        assert l[0] != '-'
        return bytes(out + [0x00])
    m = re.fullmatch(r'(├?)"(.*)"', l)
    if m:
        cs = [charcode(c) for c in chars(m.group(2))]
        if m.group(1):
            cs = [0x7F] + cs
        else:
            assert cs[0] < 0x7F, l
        assert len(cs) <= 15, l
        return bytes([0xF0 + len(cs)] + cs)
    if l in SIMPLE:
        return bytes([SIMPLE[l]])
    if l in TWOBYTE:
        return TWOBYTE[l]
    m = re.fullmatch(r'STO "(.+)"', l)
    if m:
        name = [charcode(c) for c in m.group(1)]
        return bytes([0xF0 + len(name) + 1, 0x81] + name)
    if l == 'END':
        return bytes([0xC0, 0x00, 0x0D])
    op, arg = l.split(' ', 1)
    if op == 'LBL':
        if arg.startswith('"'):
            name = [charcode(c) for c in arg.strip('"')]
            assert len(name) <= 7
            return bytes([0xC0, 0x00, 0xF0 + len(name) + 1, 0x00] + name)
        n = labcode(arg)
        if n <= 14:
            return bytes([0x01 + n])
        return bytes([0xCF, n])
    if op in ('GTO', 'XEQ'):
        if arg.startswith('"'):
            name = [charcode(c) for c in arg.strip('"')]
            return bytes([0x1D if op == 'GTO' else 0x1E, 0xF0 + len(name)] + name)
        assert not arg.startswith('IND ')
        n = labcode(arg)
        if op == 'GTO' and n <= 14:
            return bytes([0xB1 + n, 0x00])
        return bytes([0xD0 if op == 'GTO' else 0xE0, 0x00, n])
    if op == 'SIZE':
        n = int(arg)
        return bytes([0xF3, 0xF7, n >> 8, n & 0xFF])
    if op in REGOP:
        return bytes([REGOP[op], operand(arg)])
    raise ValueError('cannot encode ' + l)


def encode(text):
    out = bytearray()
    for prog in parse(text):
        for l in prog:
            out += encode_line(l)
    return bytes(out)


def screenshot(c, path, scale=2):
    from PIL import Image
    im = Image.new("L", (400, 240), 255)
    px = im.load()
    for y in range(240):
        for x in range(400):
            if c.fb[y][x]:
                px[x, y] = 0
    im.resize((400 * scale, 240 * scale), Image.NEAREST).save(path)

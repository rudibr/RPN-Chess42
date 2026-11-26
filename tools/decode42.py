import sys
from sim42 import SIMPLE, REGOP, STACKREF
RS = {v:k for k,v in SIMPLE.items()}; RR = {v:k for k,v in REGOP.items()}
SR = {v:k for k,v in STACKREF.items()}
def opnd(b):
    ind = 'IND ' if b & 0x80 else ''
    b &= 0x7F
    return ind + (SR[b] if b in SR else f"{b:02d}")
def ch(c): return '[LF]' if c==10 else (chr(c) if 32<=c<=126 and chr(c) not in '"[]' else f'[x{c:02X}]')
def lab(n):
    if 0x66<=n<=0x6F: return 'ABCDEFGHIJ'[n-0x66]
    if 0x7B<=n<=0x7F: return 'abcde'[n-0x7B]
    return f"{n:02d}"
def decode(data):
    out=[]; i=0
    while i < len(data):
        b=data[i]
        if 0x10<=b<=0x1C:
            s=''
            while i<len(data) and 0x10<=data[i]<=0x1C:
                s+= {0x1A:'.',0x1B:'E',0x1C:'-'}.get(data[i], chr(data[i]-0x10+48)); i+=1
            out.append(s)
            if i<len(data) and data[i]==0: i+=1
            continue
        if b==0x00: i+=1; continue
        if b in RS: out.append(RS[b]); i+=1; continue
        if b in RR: out.append(f"{RR[b]} {opnd(data[i+1])}"); i+=2; continue
        if 0x01<=b<=0x0F: out.append(f"LBL {b-1:02d}"); i+=1; continue
        if 0xB1<=b<=0xBF: out.append(f"GTO {b-0xB1:02d}"); i+=2; continue
        if b==0xCF: out.append(f"LBL {lab(data[i+1])}"); i+=2; continue
        if b in (0xD0,0xE0): out.append(f"{'GTO' if b==0xD0 else 'XEQ'} {lab(data[i+2]&0x7F)}"); i+=3; continue
        if b in (0x1D,0x1E):
            n=data[i+1]&0x0F; out.append(f"{'GTO' if b==0x1D else 'XEQ'} \"{''.join(map(ch,data[i+2:i+2+n]))}\""); i+=2+n; continue
        if b==0xC0:
            if data[i+2]==0x0D: out.append("END"); i+=3; continue
            n=(data[i+2]&0x0F)-1; out.append(f"LBL \"{''.join(map(ch,data[i+4:i+4+n]))}\""); i+=4+n; continue
        if b==0xA2 and data[i+1]==0x6E: out.append('GETKEY'); i+=2; continue
        if b==0xA7 and data[i+1] in (0x63,0x64,0x65): out.append({0x63:'CLLCD',0x64:'AGRAPH',0x65:'PIXEL'}[data[i+1]]); i+=2; continue
        if b==0xF3 and data[i+1]==0xF7: out.append(f"SIZE {data[i+2]*256+data[i+3]}"); i+=4; continue
        if 0xF1<=b<=0xFF:
            n=b&0x0F; body=data[i+1:i+1+n]
            if body[0]==0x81: out.append('STO "'+''.join(map(ch,body[1:]))+'"'); i+=1+n; continue
            if body[0]==0x7F: out.append('├"'+''.join(map(ch,body[1:]))+'"')
            else: out.append('"'+''.join(map(ch,body))+'"')
            i+=1+n; continue
        raise ValueError(f"byte {b:02X} at {i}")
    return out
if __name__=="__main__":
    print("\n".join(decode(open(sys.argv[1],'rb').read())))

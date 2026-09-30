#!/usr/bin/env python3
"""
gen_schematics.py -- transistor-level schematics (SVG) of the four GAA circuits.

    python3 gen_schematics.py        -> figures/schematic_{inv,nand2,ro11,sram6t}.svg (fixed colours, for PNG)
                                        and figures/schematic_*_page.svg (theme tokens, embedded in the paper)
Symbol library: MOSFET drawn at the origin (drain up, source down, gate left) and placed with a transform.
"""
import os
R = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(R, "figures")

def pal(page):
    if page:
        return dict(ink="var(--ink)", ink2="var(--ink-2)", acc="var(--accent)", bg="none", font="var(--font-ui)")
    return dict(ink="#171b22", ink2="#4b5260", acc="#1f4e8c", bg="#ffffff", font="IBM Plex Sans, system-ui, sans-serif")

TOP = 26
class S:
    def __init__(self, w, h, p):
        self.w, self.h, self.p = w, h + TOP, p
        self.head = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h + TOP}" role="img" '
                     f'style="max-width:100%;height:auto;font-family:{p["font"]};font-size:12px" '
                     f'stroke-linecap="round" stroke-linejoin="round">']
        if p["bg"] != "none":
            self.head.append(f'<rect width="{w}" height="{h + TOP}" fill="{p["bg"]}"/>')
        self.o = [f'<g transform="translate(0,{TOP})">']
    def title(self, x, s):
        self.head.append(f'<text x="{x}" y="16" text-anchor="middle" font-size="12" font-weight="600" fill="{self.p["acc"]}">{s}</text>')
    def hop(self, x, y, r=5, vertical=False):
        """gap + arc where one wire crosses another at (x, y) without connecting"""
        if vertical:
            self.o.append(f'<path d="M{x},{y - r} a{r},{r} 0 0 1 0,{2 * r}" fill="none" stroke="{self.p["ink"]}" stroke-width="1.6"/>')
        else:
            self.o.append(f'<path d="M{x - r},{y} a{r},{r} 0 0 1 {2 * r},0" fill="none" stroke="{self.p["ink"]}" stroke-width="1.6"/>')
    def line(self, x1, y1, x2, y2, w=1.6, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{self.p["ink"]}" stroke-width="{w}"{d}/>')
    def poly(self, pts, w=1.6):
        self.o.append(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" stroke="{self.p["ink"]}" stroke-width="{w}"/>')
    def dot(self, x, y): self.o.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{self.p["ink"]}"/>')
    def text(self, x, y, s, anchor="start", size=12, color=None, weight=400, italic=False):
        st = f' font-style="italic"' if italic else ""
        self.o.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" '
                      f'fill="{color or self.p["ink"]}"{st}>{s}</text>')
    def mos(self, x, y, kind, name="", rot=0, flip=False, wlabel=""):
        """MOSFET centred at (x, y): drain at (0,-30), source at (0,+30), gate lead end at (-26, 0) before transform."""
        sx = -1 if flip else 1
        g = [f'<g transform="translate({x},{y}) rotate({rot}) scale({sx},1)" stroke="{self.p["ink"]}" stroke-width="1.6" fill="none">']
        g.append('<line x1="-4" y1="-13" x2="-4" y2="13"/>')            # gate plate
        g.append('<line x1="0" y1="-11" x2="0" y2="-3"/><line x1="0" y1="-3" x2="0" y2="3"/><line x1="0" y1="3" x2="0" y2="11"/>')  # channel
        g.append('<polyline points="0,-11 12,-11 12,-30"/>')             # drain lead
        g.append('<polyline points="0,11 12,11 12,30"/>')                # source lead
        if kind == "p":
            g.append('<circle cx="-8" cy="0" r="3.5"/><line x1="-11.5" y1="0" x2="-26" y2="0"/>')
        else:
            g.append('<line x1="-4" y1="0" x2="-26" y2="0"/>')
            g.append('<polyline points="7,11 1,8 7,5" fill="none"/>')      # NMOS source arrow (points into channel)
        g.append('</g>')
        self.o.extend(g)
        if name:
            # label placed to the right of the device (un-rotated cases only)
            lx = x + (18 if not flip else -18)
            self.text(lx + (0 if not flip else 0), y + 4, name, anchor="start" if not flip else "end", size=11, color=self.p["ink2"], italic=True)
        if wlabel:
            lx = x + (18 if not flip else -18)
            self.text(lx, y + 17, wlabel, anchor="start" if not flip else "end", size=9.5, color=self.p["ink2"])
    def vdd(self, x, y, label="V<tspan font-size=\"8\" dy=\"3\">DD</tspan>"):
        self.line(x, y, x, y - 12); self.line(x - 10, y - 12, x + 10, y - 12, 2.2)
        self.text(x, y - 18, label, anchor="middle", size=11)
    def gnd(self, x, y, label="V<tspan font-size=\"8\" dy=\"3\">SS</tspan>"):
        self.line(x, y, x, y + 10); self.line(x - 10, y + 10, x + 10, y + 10, 2.2)
        self.line(x - 6, y + 15, x + 6, y + 15, 1.6); self.line(x - 2, y + 20, x + 2, y + 20, 1.2)
        self.text(x, y + 33, label, anchor="middle", size=11)
    def port(self, x, y, label, side="left"):
        if side == "left":
            self.o.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="none" stroke="{self.p["ink"]}" stroke-width="1.4"/>')
            self.text(x - 8, y + 4, label, anchor="end", size=12, weight=600)
        else:
            self.o.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="none" stroke="{self.p["ink"]}" stroke-width="1.4"/>')
            self.text(x + 8, y + 4, label, anchor="start", size=12, weight=600)
    def done(self):
        return "\n".join(self.head + self.o + ["</g>", "</svg>"])

def inverter(p):
    s = S(260, 230, p)
    x = 130
    s.vdd(x + 12, 40); s.mos(x, 70, "p", "MP", wlabel="3 sheets × 45 nm")
    s.mos(x, 150, "n", "MN", wlabel="3 sheets × 30 nm"); s.gnd(x + 12, 180)
    s.line(x + 12, 100, x + 12, 120)                                  # drain-drain
    s.line(x - 26, 70, x - 40, 70); s.line(x - 40, 70, x - 40, 150); s.line(x - 26, 150, x - 40, 150)
    s.line(x - 40, 110, x - 70, 110); s.dot(x - 40, 110); s.port(x - 74, 110, "A")
    s.line(x + 12, 110, x + 60, 110); s.dot(x + 12, 110); s.port(x + 64, 110, "Y", "right")
    s.title(x + 12, "INV_GAA_X1")
    return s.done()

def nand2(p):
    s = S(350, 300, p)
    xa, xb = 120, 224
    # parallel PMOS
    s.vdd(xa + 12, 40); s.vdd(xb + 12, 40)
    s.mos(xa, 70, "p", "MPA", wlabel="30 nm"); s.mos(xb, 70, "p", "MPB", wlabel="30 nm")
    s.line(xa + 12, 100, xa + 12, 118); s.line(xb + 12, 100, xb + 12, 118); s.line(xa + 12, 118, xb + 12, 118)
    s.dot(xa + 12, 118)
    # series NMOS
    s.mos(xa, 150, "n", "MNB", wlabel="45 nm"); s.mos(xa, 215, "n", "MNA", wlabel="45 nm")
    s.line(xa + 12, 180, xa + 12, 185); s.text(xa + 20, 186, "X", size=10, color=p["ink2"], italic=True)
    s.gnd(xa + 12, 245)
    # gates
    s.line(xa - 26, 70, xa - 50, 70); s.line(xa - 50, 70, xa - 50, 215); s.line(xa - 26, 215, xa - 50, 215)
    s.dot(xa - 50, 215); s.line(xa - 50, 215, xa - 80, 215); s.port(xa - 84, 215, "A")
    s.line(xb - 26, 70, xb - 40, 70); s.line(xb - 40, 70, xb - 40, 113); s.hop(xb - 40, 118, vertical=True); s.line(xb - 40, 123, xb - 40, 130)
    s.line(xb - 40, 130, xa - 50 + 5, 130); s.hop(xa - 50, 130); s.line(xa - 50 - 5, 130, xa - 70, 130)   # B hops over A
    s.line(xa - 26, 150, xa - 70, 150); s.line(xa - 70, 130, xa - 70, 150); s.dot(xa - 70, 150)
    s.line(xa - 70, 150, xa - 80, 150); s.port(xa - 84, 150, "B")
    # output
    s.line(xb + 12, 118, xb + 60, 118); s.port(xb + 64, 118, "Y", "right")
    s.title(175, "NAND2_GAA_X1")
    return s.done()

def ro11(p):
    n, pitch, x0 = 11, 66, 60
    s = S(x0 + n * pitch + 40, 250, p)
    top, bot = 60, 190
    s.line(x0 - 20, top, x0 + n * pitch - 10, top, 2.0); s.text(x0 - 26, top + 4, "V<tspan font-size=\"8\" dy=\"3\">DD</tspan>", anchor="end", size=11)
    s.line(x0 - 20, bot, x0 + n * pitch - 10, bot, 2.0); s.text(x0 - 26, bot + 4, "V<tspan font-size=\"8\" dy=\"3\">SS</tspan>", anchor="end", size=11)
    for i in range(n):
        x = x0 + i * pitch
        s.mos(x, 95, "p"); s.mos(x, 155, "n")
        s.line(x + 12, 65, x + 12, top); s.line(x + 12, 185, x + 12, bot)
        s.line(x - 26, 95, x - 34, 95); s.line(x - 34, 95, x - 34, 155); s.line(x - 26, 155, x - 34, 155)
        s.dot(x - 34, 125); s.dot(x + 12, 125)
        s.text(x - 6, 128, f"n{i}", size=9, color=p["ink2"], anchor="end", italic=True)
        if i < n - 1:
            s.line(x + 12, 125, x + pitch - 34, 125)                      # stage output -> next input
        else:
            s.line(x + 12, 125, x + 40, 125); s.port(x + 44, 125, "OUT", "right")
    # feedback n11 -> n0 below the VSS rail
    xl, xr = x0 - 34, x0 + (n - 1) * pitch + 12
    s.line(xr, 125, xr + 24, 125); s.line(xr + 24, 125, xr + 24, bot + 26); s.line(xr + 24, bot + 26, xl - 14, bot + 26)
    s.line(xl - 14, bot + 26, xl - 14, 125); s.line(xl - 14, 125, xl, 125)
    s.text(x0 + n * pitch / 2, bot + 44, "feedback: stage 11 output drives stage 1 input (odd number of inversions)", anchor="middle", size=10.5, color=p["ink2"])
    s.title(x0 + n * pitch / 2 - 20, "RO11_GAA: 11 × INV_GAA_X1, each node FO3-loaded (two dummy inverters per node not shown)")
    return s.done()

def sram6t(p):
    s = S(470, 290, p)
    x1, x2 = 150, 310                      # inverter 1 (gates on its right), inverter 2 (gates on its left)
    q, qb = x1 - 12, x2 + 12               # storage nodes: Q on the left of inv1, QB on the right of inv2
    g1, g2 = x1 + 40, x2 - 40              # gate bars
    for x, flip, pu, pd in ((x1, True, "PU1", "PD1"), (x2, False, "PU2", "PD2")):
        out = x - 12 if flip else x + 12
        s.vdd(out, 60); s.mos(x, 90, "p", pu, flip=flip, wlabel="20 nm")
        s.mos(x, 170, "n", pd, flip=flip, wlabel="36 nm"); s.gnd(out, 200)
        s.line(out, 120, out, 140); s.dot(out, 130)
        gx = x + 40 if flip else x - 40; lead = x + 26 if flip else x - 26
        s.line(lead, 90, gx, 90); s.line(gx, 90, gx, 170); s.line(lead, 170, gx, 170)
    # cross coupling: Q -> gate bar of inv2 on y = 118 (hops over inv1's bar), QB -> gate bar of inv1 on y = 142
    s.dot(q, 118); s.line(q, 118, g1 - 5, 118); s.hop(g1, 118); s.line(g1 + 5, 118, g2, 118); s.dot(g2, 118)
    s.dot(qb, 142); s.line(qb, 142, g2 + 5, 142); s.hop(g2, 142); s.line(g2 - 5, 142, g1, 142); s.dot(g1, 142)
    s.text(q - 22, 124, "Q", size=12, weight=600, anchor="middle"); s.text(qb + 24, 124, "QB", size=12, weight=600, anchor="middle")
    s.line(q, 130, q - 40, 130); s.line(qb, 130, qb + 40, 130)
    # access transistors: PG1 between BL and Q (gate lead points down), PG2 between QB and BLB
    for x, name in ((q - 70, "PG1"), (qb + 70, "PG2")):
        s.mos(x, 130, "n", rot=-90)                       # drain (-30,0), source (+30,0), gate lead end (0,+26)
        s.text(x, 108, name, size=11, color=p["ink2"], italic=True, anchor="middle")
        s.text(x, 158, "24 nm", size=9.5, color=p["ink2"], anchor="middle")
        s.line(x, 156, x, 250)                            # to WL
    s.line(q - 100, 130, q - 130, 130); s.line(qb + 100, 130, qb + 130, 130)
    # bit lines, word line
    for x, lab in ((q - 130, "BL"), (qb + 130, "BLB")):
        s.line(x, 40, x, 262, 2.0); s.text(x, 32, lab, anchor="middle", size=12, weight=600); s.dot(x, 130)
    s.line(q - 118, 250, qb + 118, 250, 2.0); s.dot(q - 70, 250); s.dot(qb + 70, 250)
    s.text(qb + 124, 246, "WL", anchor="end", size=12, weight=600)
    s.title(235, "SRAM6T_GAA_HD (thin cell): PD 36 / PG 24 / PU 20-nm sheets")
    return s.done()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("inv", inverter), ("nand2", nand2), ("ro11", ro11), ("sram6t", sram6t)):
        open(os.path.join(OUT, f"schematic_{name}.svg"), "w").write(fn(pal(False)))
        open(os.path.join(OUT, f"schematic_{name}_page.svg"), "w").write(fn(pal(True)))
    print("schematics written to", OUT)

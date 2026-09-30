#!/usr/bin/env python3
"""
gen_schematics_virtuoso.py -- the four schematics drawn in the Cadence Virtuoso Schematic
Editor convention: black canvas with dot grid, device symbols (analogLib nmos4/pmos4 style,
4 terminals) on the red 'device' layer, wires on the blue 'wire' layer, instance names and
parameter annotations in yellow, iopin symbols in red, window frame with the editor banner.
These are renderings in the editor's style, not screenshots; replace them with captures from
the VMware guest for the camera-ready manuscript.

    python3 gen_schematics_virtuoso.py   -> figures/virtuoso_{inv,nand2,ro11,sram6t}.svg
"""
import os
R = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(R, "figures")
C = dict(bg="#000000", grid="#3a3a3a", dev="#ff3b30", wire="#4f8cff", ann="#ffd21f", pin="#ff3b30",
         net="#8fb4ff", chrome="#d9d9d9", chrome2="#f2f2f2", chrome_ink="#1a1a1a", sel="#0c5cc4")
FONT = "'DejaVu Sans Mono', 'Liberation Mono', Menlo, monospace"

class V:
    def __init__(self, w, h, cell):
        self.w, self.h, self.cell = w, h, cell
        self.T, self.B = 46, 22                      # chrome heights
        self.o = []
    def line(self, x1, y1, x2, y2, col=None, w=1.5):
        self.o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col or C["wire"]}" stroke-width="{w}"/>')
    def wire(self, pts):
        self.o.append(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" stroke="{C["wire"]}" stroke-width="1.6"/>')
    def dot(self, x, y): self.o.append(f'<circle cx="{x}" cy="{y}" r="2.6" fill="{C["wire"]}"/>')
    def text(self, x, y, s, col, size=10, anchor="start", weight=400):
        self.o.append(f'<text x="{x}" y="{y}" fill="{col}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>')
    def mos(self, x, y, kind, inst, model, hfin, flip=False, rot=0):
        sx = -1 if flip else 1
        g = [f'<g transform="translate({x},{y}) rotate({rot}) scale({sx},1)" stroke="{C["dev"]}" stroke-width="1.5" fill="none">',
             '<line x1="-30" y1="0" x2="-9" y2="0"/>',                     # gate lead (G pin at -30,0)
             '<line x1="-9" y1="-12" x2="-9" y2="12"/>',                    # gate plate
             '<line x1="-4" y1="-14" x2="-4" y2="14" stroke-width="3"/>',   # channel (thick, Virtuoso style)
             '<polyline points="-4,-12 8,-12 8,-30"/>',                     # drain lead (D pin at 8,-30)
             '<polyline points="-4,12 8,12 8,30"/>',                        # source lead (S pin at 8,30)
             '<line x1="-4" y1="0" x2="22" y2="0"/>']                       # bulk lead (B pin at 22,0)
        if kind == "n":
            g.append('<polyline points="4,-4 -4,0 4,4" />')                # bulk arrow pointing into the channel
        else:
            g.append('<circle cx="-13" cy="0" r="3.2"/><polyline points="4,-4 10,0 4,4"/>')
            g[1] = '<line x1="-30" y1="0" x2="-16" y2="0"/>'
        g.append('</g>')
        self.o.extend(g)
        ax = x + (40 if not flip else -40); anc = "start" if not flip else "end"
        self.text(ax, y - 6, inst, C["ann"], 9.5, anc, 600)
        self.text(ax, y + 5, model, C["ann"], 8.5, anc)
        self.text(ax, y + 15, f"hfin={hfin}n nfin=3 l=14n", C["ann"], 8.5, anc)
    def vdd(self, x, y, name="vdd!"):
        self.o.append(f'<g stroke="{C["dev"]}" stroke-width="1.5" fill="none"><line x1="{x}" y1="{y}" x2="{x}" y2="{y-10}"/>'
                      f'<line x1="{x-9}" y1="{y-10}" x2="{x+9}" y2="{y-10}" stroke-width="2.2"/></g>')
        self.text(x, y - 14, name, C["dev"], 9, "middle")
    def gnd(self, x, y, name="gnd!"):
        self.o.append(f'<g stroke="{C["dev"]}" stroke-width="1.5" fill="none"><line x1="{x}" y1="{y}" x2="{x}" y2="{y+8}"/>'
                      f'<line x1="{x-9}" y1="{y+8}" x2="{x+9}" y2="{y+8}" stroke-width="2.2"/><line x1="{x-5}" y1="{y+13}" x2="{x+5}" y2="{y+13}"/>'
                      f'<line x1="{x-2}" y1="{y+18}" x2="{x+2}" y2="{y+18}"/></g>')
        self.text(x, y + 30, name, C["dev"], 9, "middle")
    def iopin(self, x, y, name, direction):
        """basic-lib iopin: input = arrow box pointing right, output = box with arrow tip, drawn on the pin layer"""
        if direction == "in":
            pts = f"{x-34},{y-6} {x-10},{y-6} {x-4},{y} {x-10},{y+6} {x-34},{y+6}"
            self.text(x - 22, y + 3.5, name, C["pin"], 9, "middle", 600)
        else:
            pts = f"{x+4},{y-6} {x+28},{y-6} {x+34},{y} {x+28},{y+6} {x+4},{y+6} {x+10},{y}"
            self.text(x + 18, y + 3.5, name, C["pin"], 9, "middle", 600)
        self.o.append(f'<polygon points="{pts}" fill="none" stroke="{C["pin"]}" stroke-width="1.4"/>')
    def inv_symbol(self, x, y, inst):
        """INV_GAA_X1 symbol instance: input pin at (x-30,y), output at (x+34,y)"""
        self.o.append(f'<g stroke="{C["dev"]}" stroke-width="1.5" fill="none"><polygon points="{x-14},{y-16} {x-14},{y+16} {x+14},{y}"/>'
                      f'<circle cx="{x+18}" cy="{y}" r="3.5"/><line x1="{x-30}" y1="{y}" x2="{x-14}" y2="{y}"/>'
                      f'<line x1="{x+21.5}" y1="{y}" x2="{x+34}" y2="{y}"/></g>')
        self.text(x, y - 22, inst, C["ann"], 9, "middle", 600); self.text(x, y + 30, "INV_GAA_X1", C["ann"], 8, "middle")
    def done(self):
        w, h, T, B = self.w, self.h, self.T, self.B
        head = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h + T + B}" role="img" style="max-width:100%;height:auto;font-family:{FONT}" stroke-linecap="round" stroke-linejoin="round">',
                f'<rect width="{w}" height="{h + T + B}" fill="{C["chrome"]}"/>',
                # title bar + menu
                f'<rect x="0" y="0" width="{w}" height="22" fill="{C["sel"]}"/>',
                f'<text x="8" y="15" fill="#ffffff" font-size="10.5" font-weight="600">Virtuoso® Schematic Editor L  Editing: GAA3_INV_LIB {self.cell} schematic</text>',
                f'<text x="{w-8}" y="15" fill="#ffffff" font-size="10" text-anchor="end">–  □  ×</text>',
                f'<rect x="0" y="22" width="{w}" height="24" fill="{C["chrome2"]}"/>',
                f'<text x="8" y="38" fill="{C["chrome_ink"]}" font-size="10">Launch   File   Edit   View   Create   Check   Options   Migrate   Window   Help</text>',
                f'<text x="{w-8}" y="38" fill="{C["chrome_ink"]}" font-size="10" text-anchor="end">cādence</text>',
                # canvas with dot grid
                f'<rect x="0" y="{T}" width="{w}" height="{h}" fill="{C["bg"]}"/>',
                '<defs><pattern id="vgrid" width="20" height="20" patternUnits="userSpaceOnUse">'
                f'<circle cx="10" cy="10" r="0.8" fill="{C["grid"]}"/></pattern></defs>',
                f'<rect x="0" y="{T}" width="{w}" height="{h}" fill="url(#vgrid)"/>',
                f'<g transform="translate(0,{T})">']
        tail = ['</g>',
                f'<rect x="0" y="{T+h}" width="{w}" height="{B}" fill="{C["chrome2"]}"/>',
                f'<text x="8" y="{T+h+15}" fill="{C["chrome_ink"]}" font-size="9">mouse L: schSingleSelectPt()     M: schHiMousePopUp()     R: schHiMouseHelp()</text>',
                f'<text x="{w-8}" y="{T+h+15}" fill="{C["chrome_ink"]}" font-size="9" text-anchor="end">Cmd:   Sel: 0   |  {self.cell}</text>',
                '</svg>']
        return "\n".join(head + self.o + tail)

def inverter():
    v = V(560, 250, "INV_GAA_X1"); x = 270
    v.vdd(x + 8, 50); v.mos(x, 80, "p", "MP0", "nsheet_p", 45); v.mos(x, 160, "n", "MN0", "nsheet_n", 30); v.gnd(x + 8, 190)
    v.wire([(x + 8, 110), (x + 8, 130)]); v.wire([(x + 22, 80), (x + 30, 80), (x + 30, 50), (x + 8, 50)])   # bulk P -> vdd!
    v.wire([(x + 22, 160), (x + 30, 160), (x + 30, 190), (x + 8, 190)])                                    # bulk N -> gnd!
    v.wire([(x - 30, 80), (x - 50, 80), (x - 50, 160), (x - 30, 160)]); v.dot(x - 50, 120)
    v.wire([(x - 50, 120), (x - 90, 120)]); v.iopin(x - 90, 120, "A", "in")
    v.wire([(x + 8, 120), (x + 70, 120)]); v.dot(x + 8, 120); v.iopin(x + 70, 120, "Y", "out")
    v.text(x - 46, 114, "A", C["net"], 8.5); v.text(x + 40, 114, "Y", C["net"], 8.5)
    return v.done()

def nand2():
    v = V(620, 310, "NAND2_GAA_X1"); xa, xb = 190, 400
    for x, inst in ((xa, "MP0"), (xb, "MP1")):
        v.vdd(x + 8, 50); v.mos(x, 80, "p", inst, "nsheet_p", 30)
        v.wire([(x + 22, 80), (x + 30, 80), (x + 30, 50), (x + 8, 50)])
    v.wire([(xa + 8, 110), (xa + 8, 130)]); v.wire([(xb + 8, 110), (xb + 8, 130), (xa + 8, 130)]); v.dot(xa + 8, 130)
    v.mos(xa, 165, "n", "MN1", "nsheet_n", 45); v.mos(xa, 235, "n", "MN0", "nsheet_n", 45); v.gnd(xa + 8, 265)
    v.wire([(xa + 8, 195), (xa + 8, 205)]); v.text(xa - 14, 204, "net_x", C["net"], 8, "end")
    v.wire([(xa + 22, 165), (xa + 30, 165), (xa + 30, 205), (xa + 8, 205)])                 # MN1 bulk to its source
    v.wire([(xa + 22, 235), (xa + 30, 235), (xa + 30, 265), (xa + 8, 265)])
    v.wire([(xa - 30, 80), (xa - 60, 80), (xa - 60, 235), (xa - 30, 235)]); v.dot(xa - 60, 235)
    v.wire([(xa - 60, 235), (xa - 100, 235)]); v.iopin(xa - 100, 235, "A", "in")
    v.wire([(xb - 30, 80), (xb - 44, 80), (xb - 44, 140), (xa - 80, 140), (xa - 80, 165), (xa - 30, 165)]); v.dot(xa - 80, 165)
    v.wire([(xa - 80, 165), (xa - 100, 165)]); v.iopin(xa - 100, 165, "B", "in")
    v.wire([(xa + 8, 130), (xb + 70, 130)]); v.iopin(xb + 70, 130, "Y", "out")
    v.text(xb + 30, 124, "Y", C["net"], 8.5)
    return v.done()

def ro11():
    n, pitch, x0 = 11, 62, 70
    v = V(x0 + n * pitch + 60, 190, "RO11_GAA")
    for i in range(n):
        x = x0 + i * pitch
        v.inv_symbol(x, 90, f"I{i}")
        if i < n - 1: v.wire([(x + 34, 90), (x + pitch - 30, 90)]); v.text(x + 40, 84, f"n{i+1}", C["net"], 7.5)
    xl, xr = x0 - 30, x0 + (n - 1) * pitch + 34
    v.wire([(xr, 90), (xr + 16, 90)]); v.dot(xr + 16, 90); v.wire([(xr + 16, 90), (xr + 16, 150), (xl - 16, 150), (xl - 16, 90), (xl, 90)])
    v.text(x0 + n * pitch / 2, 164, "n0 (feedback)", C["net"], 8, "middle")
    v.wire([(xr + 16, 90), (xr + 44, 90)]); v.iopin(xr + 44, 90, "OUT", "out")
    return v.done()

def sram6t():
    v = V(840, 300, "SRAM6T_GAA_HD"); x1, x2 = 320, 500
    q, qb = x1 - 8, x2 + 8; g1, g2 = x1 + 44, x2 - 44
    PG, BLX = 170, 220                                   # access transistor / bit line offsets from the storage nodes
    for x, flip, pu, pd in ((x1, True, "MPU0", "MPD0"), (x2, False, "MPU1", "MPD1")):
        out = x - 8 if flip else x + 8; bx = x - 22 if flip else x + 22; bo = x - 34 if flip else x + 34
        v.vdd(out, 50); v.mos(x, 80, "p", pu, "nsheet_p", 20, flip=flip); v.mos(x, 160, "n", pd, "nsheet_n", 36, flip=flip); v.gnd(out, 190)
        v.wire([(out, 110), (out, 130)]); v.wire([(bx, 80), (bo, 80), (bo, 50), (out, 50)]); v.wire([(bx, 160), (bo, 160), (bo, 190), (out, 190)])
        gx = x + 44 if flip else x - 44; lead = x + 30 if flip else x - 30
        v.wire([(lead, 80), (gx, 80), (gx, 160), (lead, 160)])
    v.dot(q, 118); v.wire([(q, 118), (g1 - 5, 118)]); v.o.append(f'<path d="M{g1-5},118 a5,5 0 0 1 10,0" fill="none" stroke="{C["wire"]}" stroke-width="1.6"/>'); v.wire([(g1 + 5, 118), (g2, 118)]); v.dot(g2, 118)
    v.dot(qb, 142); v.wire([(qb, 142), (g2 + 5, 142)]); v.o.append(f'<path d="M{g2+5},142 a5,5 0 0 0 -10,0" fill="none" stroke="{C["wire"]}" stroke-width="1.6"/>'); v.wire([(g2 - 5, 142), (g1, 142)]); v.dot(g1, 142)
    v.text(q - 14, 112, "Q", C["net"], 9, "middle", 600); v.text(qb + 16, 156, "QB", C["net"], 9, "middle", 600)
    for x, inst in ((q - PG, "MPG0"), (qb + PG, "MPG1")):
        v.o.append(f'<g transform="translate({x},130) rotate(-90)" stroke="{C["dev"]}" stroke-width="1.5" fill="none">'
                   '<line x1="-30" y1="0" x2="-9" y2="0"/><line x1="-9" y1="-12" x2="-9" y2="12"/><line x1="-4" y1="-14" x2="-4" y2="14" stroke-width="3"/>'
                   '<polyline points="-4,-12 8,-12 8,-30"/><polyline points="-4,12 8,12 8,30"/><line x1="-4" y1="0" x2="22" y2="0"/><polyline points="4,-4 -4,0 4,4"/></g>')
        v.text(x, 78, inst, C["ann"], 9, "middle", 600); v.text(x, 89, "nsheet_n", C["ann"], 8, "middle"); v.text(x, 100, "hfin=24n", C["ann"], 8, "middle")
        v.wire([(x, 152), (x, 250)])                                   # gate lead (rotated symbol) down to WL
        v.wire([(x, 108), (x + 14, 108), (x + 14, 130 + 30 - 8), (x + 30, 130)]) if False else None
    v.wire([(q - PG - 30, 130), (q - BLX, 130)]); v.wire([(q - PG + 30, 130), (q, 130)])
    v.wire([(qb + PG - 30, 130), (qb, 130)]); v.wire([(qb + PG + 30, 130), (qb + BLX, 130)])
    for x, lab in ((q - BLX, "BL"), (qb + BLX, "BLB")):
        v.wire([(x, 40), (x, 262)]); v.text(x + 8 if lab == "BL" else x - 8, 44, lab, C["net"], 9, "start" if lab == "BL" else "end", 600); v.dot(x, 130)
    v.wire([(q - BLX + 12, 250), (qb + BLX - 12, 250)]); v.dot(q - PG, 250); v.dot(qb + PG, 250)
    v.text(qb + BLX - 20, 246, "WL", C["net"], 9, "end", 600)
    v.iopin(q - BLX, 20, "BL", "in"); v.iopin(qb + BLX, 20, "BLB", "in"); v.iopin(qb + BLX + 8, 250, "WL", "out")
    return v.done()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("inv", inverter), ("nand2", nand2), ("ro11", ro11), ("sram6t", sram6t)):
        open(os.path.join(OUT, f"virtuoso_{name}.svg"), "w").write(fn())
    print("virtuoso-style schematics written")

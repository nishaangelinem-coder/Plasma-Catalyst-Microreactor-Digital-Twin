#!/usr/bin/env python3
"""
gen_gaa_ro_gds.py -- hierarchical GDSII of an 11-stage GAA ring oscillator (RO11_GAA).

Eleven INV_GAA_X1 cells are abutted on one 168-nm row (shared dummy gates and
rails); stage i output Y is wired to stage i+1 input A on metal-2 (layer 9) with
via-1 (layer 8), and the last output feeds back to the first input on a second
M2 track.  Writes gaa_ro11.gds (SREF hierarchy) and gaa_ro11.svg (flattened).
"""
import gen_gaa_inverter_gds as inv

N = 11
CW, CH = inv.CELL_W, inv.CELL_H
L_V1, L_M2, L_M2PIN, L_M2TXT = (8, 0), (9, 0), (9, 1), (9, 2)
Y_A = CH // 2                 # input pad row  (y = 84)
X_A, X_Y = 48, 69             # A pad and Y bar centres inside a cell
M2W, V1 = 16, 10
inv.STYLE.update({L_V1: ("#ffeb3b", "#8d6e00", 1.0), L_M2: ("#8e24aa", "#4a148c", 0.55), L_M2PIN: ("none", "#4a148c", 1.0)})

def build_ro(cell_inv):
    ro = inv.GdsCell("RO11_GAA")
    flat = inv.GdsCell("RO11_GAA_flat")          # render-only copy
    for i in range(N):
        ro.ref(cell_inv.name, i * CW, 0)
        for layer, dt, pts, tag in cell_inv.polygons:
            flat.polygons.append((layer, dt, [(x + i * CW, y) for x, y in pts], f"inv{i} {tag}"))
    def wire(c):
        v = V1 // 2
        for i in range(N - 1):                    # Y_i -> A_{i+1} on M2 track y = 84
            x0, x1 = i * CW + X_Y, (i + 1) * CW + X_A
            c.rect(*L_M2, x0 - M2W // 2, Y_A - M2W // 2, x1 + M2W // 2, Y_A + M2W // 2, f"net n{i+1}")
            c.rect(*L_V1, x0 - v, Y_A - v, x0 + v, Y_A + v, "V1")
            c.rect(*L_V1, x1 - v, Y_A - v, x1 + v, Y_A + v, "V1")
        # feedback: Y_10 -> A_0 on M2 track y = 112, drop to y = 84 at x = 48
        xl, xf, yt = (N - 1) * CW + X_Y, X_A, Y_A + 28
        c.rect(*L_M2, xf - M2W // 2, yt - M2W // 2, xl + M2W // 2, yt + M2W // 2, "net n0 (feedback)")
        c.rect(*L_M2, xf - M2W // 2, Y_A - M2W // 2, xf + M2W // 2, yt + M2W // 2, "net n0")
        c.rect(*L_V1, xl - v, yt - v, xl + v, yt + v, "V1")
        c.rect(*L_V1, xf - v, Y_A - v, xf + v, Y_A + v, "V1")
        c.rect(*L_M2PIN, xl - M2W // 2, yt - M2W // 2, xl + M2W // 2, yt + M2W // 2, "OUT pin")
        c.label(*L_M2TXT, xl, yt, "OUT")
        c.rect(*inv.L["PRBOUND"], 0, 0, N * CW, CH, "prBoundary")
    wire(ro); wire(flat)
    return ro, flat

if __name__ == "__main__":
    lib = inv.GdsLibrary("GAA3_INV_LIB")
    cell_inv = inv.build_inverter()
    ro, flat = build_ro(cell_inv)
    lib.cells += [cell_inv, ro]
    lib.write("gaa_ro11.gds")
    open("gaa_ro11.svg", "w").write(inv.to_svg(flat, pad=16, scale=1.6))
    print(f"wrote gaa_ro11.gds: RO11_GAA = {N} x {cell_inv.name} refs + {len(ro.polygons)} wiring polygons, "
          f"{N*CW} x {CH} nm, area {N*CW*CH/1e6:.4f} um^2")

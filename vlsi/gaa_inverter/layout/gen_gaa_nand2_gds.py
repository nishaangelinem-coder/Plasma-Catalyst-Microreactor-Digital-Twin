#!/usr/bin/env python3
"""
gen_gaa_nand2_gds.py -- GDSII of the two-input NAND standard cell NAND2_GAA_X1.

3 contacted gate pitches wide (144 nm) on the same 6-track 168-nm template as the
inverter.  GAA-specific sizing: the series NMOS stack uses 45-nm sheets and the two
parallel PMOS use 30-nm sheets (the bands are swapped relative to the inverter), which
balances worst-case pull-up and pull-down without changing the cell footprint.
Topology:  PMOS  VDD -(A)- Y -(B)- VDD   |   NMOS  VSS -(A)- X -(B)- Y
In-cell routing: M1 (layer 7) vertical stubs/straps, output on M2 (layer 9) via V1 (layer 8).
"""
import gen_gaa_inverter_gds as inv

L = inv.L
L_V1, L_M2, L_M2PIN, L_M2TXT = (8, 0), (9, 0), (9, 1), (9, 2)
inv.STYLE.update({L_V1: ("#ffeb3b", "#8d6e00", 1.0), L_M2: ("#8e24aa", "#4a148c", 0.55), L_M2PIN: ("none", "#4a148c", 1.0)})
CPP, LG, CH = inv.TECH["CPP"], inv.TECH["LG"], inv.CELL_H
CW = 3 * CPP                                   # 144 nm
NS_W_N, NS_W_P = 45, 30                        # swapped relative to INV_GAA_X1
SD, M1W, V0, RW = 20, 16, 10, inv.TECH["RAIL_W"] // 2

def build_nand2():
    c = inv.GdsCell("NAND2_GAA_X1")
    lg2 = LG // 2
    c.rect(*L["PRBOUND"], 0, 0, CW, CH, "prBoundary")
    c.rect(*L["NWELL"], 0, CH // 2, CW, CH, "NWELL")
    # nanosheet bands: N 45 nm (y 24..69), P 30 nm (y 104..134); mid gap 35 nm for gate contacts
    n_y0, n_y1 = 24, 24 + NS_W_N
    p_y1 = CH - 34; p_y0 = p_y1 - NS_W_P
    c.rect(*L["NSHEET"], 8, n_y0, CW - 8, n_y1, "NS_N (45 nm, series stack)")
    c.rect(*L["NSHEET"], 8, p_y0, CW - 8, p_y1, "NS_P (30 nm, parallel)")
    for i in range(3):
        dy_n = n_y0 + 5 + i * ((NS_W_N - 10) // 3); dy_p = p_y0 + 4 + i * ((NS_W_P - 8) // 3)
        c.rect(*L["NS_STACK_MARK"], 10, dy_n, CW - 10, dy_n + 2, "sheet")
        c.rect(*L["NS_STACK_MARK"], 10, dy_p, CW - 10, dy_p + 2, "sheet")
    # gates: A at x=48, B at x=96, half dummies at the edges
    gates = {"A": CPP, "B": 2 * CPP}
    for name, gx in gates.items():
        c.rect(*L["GATE"], gx - lg2, 14, gx + lg2, CH - 14, f"gate {name}")
    c.rect(*L["GATE"], -lg2, 14, lg2, CH - 14, "dummy")
    c.rect(*L["GATE"], CW - lg2, 14, CW + lg2, CH - 14, "dummy")
    # S/D trench contacts in the three diffusion slots (x centres 24, 72, 120)
    slots = [24, 72, 120]
    for x in slots:
        c.rect(*L["SDC"], x - SD // 2, n_y0 - 2, x + SD // 2, n_y1 + 2, "SDC N")
        c.rect(*L["SDC"], x - SD // 2, p_y0 - 2, x + SD // 2, p_y1 + 2, "SDC P")
    # gate contacts in the mid region (y 69..104)
    ym = (n_y1 + p_y0) // 2                    # 86
    for name, gx in gates.items():
        c.rect(*L["CB"], gx - lg2 - 2, ym - 8, gx + lg2 + 2, ym + 8, f"CB {name}")
    # rails
    c.rect(*L["M1"], -4, -RW, CW + 4, RW, "VSS rail")
    c.rect(*L["M1"], -4, CH - RW, CW + 4, CH + RW, "VDD rail")
    v = V0 // 2; ny, py = (n_y0 + n_y1) // 2, (p_y0 + p_y1) // 2
    def via0(x, y): c.rect(*L["V0"], x - v, y - v, x + v, y + v, "V0")
    # NMOS: slot0 = VSS source, slot1 = internal node X (contact only), slot2 = Y drain
    c.rect(*L["M1"], 24 - M1W // 2, 0, 24 + M1W // 2, n_y1, "VSS strap"); via0(24, ny)
    c.rect(*L["M1"], 120 - M1W // 2, n_y0, 120 + M1W // 2, n_y1, "Y stub (N drain)"); via0(120, ny)
    # PMOS: slot0 = VDD, slot1 = Y drain (shared), slot2 = VDD
    c.rect(*L["M1"], 24 - M1W // 2, p_y0, 24 + M1W // 2, CH, "VDD strap"); via0(24, py)
    c.rect(*L["M1"], 120 - M1W // 2, p_y0, 120 + M1W // 2, CH, "VDD strap"); via0(120, py)
    c.rect(*L["M1"], 72 - M1W // 2, p_y0, 72 + M1W // 2, p_y1, "Y stub (P drain)"); via0(72, py)
    # input pads on M1 track y=86, 16 nm wide, A centred 48, B centred 92 (12-nm spacing to Y column)
    for name, xc in (("A", 48), ("B", 92)):
        c.rect(*L["M1"], xc - 8, ym - 8, xc + 8, ym + 8, f"{name} pad")
        c.rect(*L["M1_PIN"], xc - 8, ym - 8, xc + 8, ym + 8, f"{name} pin")
        via0(xc, ym); c.label(*L["M1_TEXT"], xc, ym, name)
    # output net on M2: V1 on the P-drain stub, horizontal to x=120, vertical down to V1 on the N-drain stub
    c.rect(*L_V1, 72 - v, py - v, 72 + v, py + v, "V1"); c.rect(*L_V1, 120 - v, ny - v, 120 + v, ny + v, "V1")
    c.rect(*L_M2, 72 - M1W // 2, py - M1W // 2, 120 + M1W // 2, py + M1W // 2, "Y (M2)")
    c.rect(*L_M2, 120 - M1W // 2, ny - M1W // 2, 120 + M1W // 2, py + M1W // 2, "Y (M2)")
    c.rect(*L_M2PIN, 120 - M1W // 2, ym - 8, 120 + M1W // 2, ym + 8, "Y pin")
    c.label(*L_M2TXT, 120, ym, "Y")
    c.label(*L["M1_TEXT"], CW // 2, CH, "VDD"); c.label(*L["M1_TEXT"], CW // 2, 0, "VSS")
    return c

if __name__ == "__main__":
    lib = inv.GdsLibrary("GAA3_INV_LIB")
    nand = build_nand2()
    lib.cells.append(nand)
    lib.write("gaa_nand2.gds")
    open("gaa_nand2.svg", "w").write(inv.to_svg(nand))
    print(f"wrote gaa_nand2.gds  {nand.name}  {CW}x{CH} nm  {len(nand.polygons)} polygons  "
          f"{len(nand.labels)} labels  area {CW*CH/1e6:.4f} um^2")

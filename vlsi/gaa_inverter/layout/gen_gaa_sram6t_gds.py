#!/usr/bin/env python3
"""
gen_gaa_sram6t_gds.py -- GDSII of a 6T GAA nanosheet SRAM bitcell (SRAM6T_GAA_HD).

Thin-cell topology (Osada et al.): four vertical nanosheet stripes (N | P | P | N), two
horizontal gate rows at the 48-nm contacted gate pitch, cross-coupling through butted
(gate + S/D) contacts.  Cell: 216 x 96 nm = 0.0207 um^2 (3-nm-class high-density).
GAA-specific: the NMOS stripe is jogged so PD uses 36-nm sheets and PG 24-nm sheets
(beta = 1.41) while PU uses 20-nm sheets (gamma = 1.55); a FinFET HD cell is stuck at 1-1-1 fins.
Metal: M1 local nets/pads, M2 BL / VSS / VDD / VSS / BLB vertical, M3 WL horizontal.
"""
import gen_gaa_inverter_gds as inv

L = inv.L
L_V1, L_M2, L_M2PIN, L_M2TXT = (8, 0), (9, 0), (9, 1), (9, 2)
L_V2, L_M3, L_M3TXT = (10, 0), (11, 0), (11, 2)
inv.STYLE.update({L_V1: ("#ffeb3b", "#8d6e00", 1.0), L_M2: ("#8e24aa", "#4a148c", 0.55), L_M2PIN: ("none", "#4a148c", 1.0),
                  L_V2: ("#ff7043", "#bf360c", 1.0), L_M3: ("#00897b", "#004d40", 0.45)})
CW, CH = 216, 96
LG = 14

def build_sram():
    c = inv.GdsCell("SRAM6T_GAA_HD")
    c.rect(*L["PRBOUND"], 0, 0, CW, CH, "prBoundary")
    c.rect(*L["NWELL"], 60, -4, 156, CH + 4, "NWELL")
    # ---- nanosheet stripes (x = along WL, y = along BL) --------------------------------
    c.rect(*L["NSHEET"], 10, 36, 46, CH + 4, "N-left: PD1 (36 nm)")      # PD1 region + VSS
    c.rect(*L["NSHEET"], 16, -4, 40, 40, "N-left: PG1 (24 nm)")           # PG1 region + BL
    c.rect(*L["NSHEET"], 72, 20, 92, CH + 4, "P-left: PU1 (20 nm)")
    c.rect(*L["NSHEET"], 124, -4, 144, 76, "P-right: PU2 (20 nm)")
    c.rect(*L["NSHEET"], 170, -4, 206, 60, "N-right: PD2 (36 nm)")
    c.rect(*L["NSHEET"], 176, 56, 200, CH + 4, "N-right: PG2 (24 nm)")
    # ---- gate rows: upper y 65..79, lower y 17..31 --------------------------------------
    c.rect(*L["GATE"], 0, 65, 112, 79, "gate A: PD1+PU1 (driven by QB)")
    c.rect(*L["GATE"], 160, 65, CW, 79, "gate PG2 (WL)")
    c.rect(*L["GATE"], 104, 17, CW, 31, "gate B: PU2+PD2 (driven by Q)")
    c.rect(*L["GATE"], 0, 17, 56, 31, "gate PG1 (WL)")
    c.rect(*L["GATE_CUT"], 112, 63, 160, 81, "gate cut"); c.rect(*L["GATE_CUT"], 56, 15, 104, 33, "gate cut")
    # ---- S/D and butted contacts ------------------------------------------------------------
    c.rect(*L["SDC"], 16, -6, 40, 8, "BL contact");         c.rect(*L["SDC"], 10, 88, 46, 102, "VSS contact")
    c.rect(*L["SDC"], 10, 41, 46, 55, "Q node (N)")
    c.rect(*L["SDC"], 176, 88, 200, 102, "BLB contact");    c.rect(*L["SDC"], 170, -6, 206, 8, "VSS contact")
    c.rect(*L["SDC"], 170, 41, 206, 55, "QB node (N)")
    c.rect(*L["SDC"], 72, 84, 92, 102, "VDD contact");      c.rect(*L["SDC"], 124, -6, 144, 12, "VDD contact")
    c.rect(*L["SDC"], 72, 20, 92, 55, "Q node (P drain)");  c.rect(*L["SDC"], 72, 20, 114, 34, "butted: Q -> gate B")
    c.rect(*L["SDC"], 124, 41, 144, 76, "QB node (P drain)"); c.rect(*L["SDC"], 102, 62, 144, 76, "butted: QB -> gate A")
    c.rect(*L["CB"], 102, 17, 114, 31, "CB gate B end");    c.rect(*L["CB"], 102, 65, 114, 79, "CB gate A end")
    c.rect(*L["CB"], 0, 17, 10, 31, "CB PG1 (WL)");        c.rect(*L["CB"], 206, 65, CW, 79, "CB PG2 (WL)")
    v = 5
    def via(layer, x, y, tag): c.rect(*layer, x - v, y - v, x + v, y + v, tag)
    # ---- M1: node straps and pads ----------------------------------------------------------------
    c.rect(*L["M1"], 20, 41, 96, 55, "Q strap");  via(L["V0"], 28, 48, "V0"); via(L["V0"], 82, 48, "V0")
    c.rect(*L["M1"], 120, 41, 196, 55, "QB strap"); via(L["V0"], 134, 48, "V0"); via(L["V0"], 188, 48, "V0")
    c.rect(*L["M1"], 24, -4, 40, 12, "BL pad");   via(L["V0"], 32, 4, "V0")
    c.rect(*L["M1"], 176, 84, 192, 100, "BLB pad"); via(L["V0"], 184, 92, "V0")
    c.rect(*L["M1"], 10, 84, 66, 100, "VSS pad");  via(L["V0"], 28, 92, "V0")
    c.rect(*L["M1"], 150, -4, 206, 12, "VSS pad"); via(L["V0"], 188, 4, "V0")
    c.rect(*L["M1"], 80, 84, 116, 100, "VDD pad"); via(L["V0"], 84, 92, "V0")
    c.rect(*L["M1"], 100, -4, 140, 12, "VDD pad"); via(L["V0"], 134, 4, "V0")
    c.rect(*L["M1"], -3, 17, 13, 31, "WL pad");    via(L["V0"], 5, 24, "V0")
    c.rect(*L["M1"], 203, 65, 219, 79, "WL pad");  via(L["V0"], 211, 72, "V0")
    # ---- M2: BL / VSS / VDD / VSS / BLB vertical, WL stubs -----------------------------------------
    for x, name in ((32, "BL"), (60, "VSS"), (108, "VDD"), (156, "VSS"), (184, "BLB")):
        c.rect(*L_M2, x - 8, -6, x + 8, CH + 6, f"{name} (M2)")
        c.label(*L_M2TXT, x, CH // 2 + (12 if name in ("BL", "BLB") else -12), name)
    via(L_V1, 32, 4, "V1 BL"); via(L_V1, 184, 92, "V1 BLB")
    via(L_V1, 60, 92, "V1 VSS"); via(L_V1, 156, 4, "V1 VSS")
    via(L_V1, 108, 92, "V1 VDD"); via(L_V1, 108, 4, "V1 VDD")
    c.rect(*L_M2, -3, 17, 13, 56, "WL stub"); via(L_V1, 5, 24, "V1 WL"); via(L_V2, 5, 48, "V2 WL")
    c.rect(*L_M2, 203, 40, 219, 79, "WL stub"); via(L_V1, 211, 72, "V1 WL"); via(L_V2, 211, 48, "V2 WL")
    # ---- M3: word line ----------------------------------------------------------------------------------
    c.rect(*L_M3, -6, 40, CW + 6, 56, "WL (M3)"); c.label(*L_M3TXT, CW // 2, 48, "WL")
    c.label(*L["M1_TEXT"], 28, 48, "Q"); c.label(*L["M1_TEXT"], 188, 48, "QB")
    return c

if __name__ == "__main__":
    lib = inv.GdsLibrary("GAA3_INV_LIB")
    cell = build_sram()
    lib.cells.append(cell)
    lib.write("gaa_sram6t.gds")
    open("gaa_sram6t.svg", "w").write(inv.to_svg(cell, pad=16, scale=3.0))
    print(f"wrote gaa_sram6t.gds  {cell.name}  {CW}x{CH} nm  {len(cell.polygons)} polygons  "
          f"{len(cell.labels)} labels  area {CW*CH/1e6:.4f} um^2")

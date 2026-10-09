"""
Generate the tape-out candidate layout (GDSII) of the CMOS driver die for the
STM acoustic circulator with gdstk, using a generic 65 nm 1P9M layer map.

Blocks: pad ring (GSG RF pads x3, DC/clock pads), three wide nMOS switches with
their MIM capacitors (C_sw, C_sh), three tapered driver chains, the Johnson phase
generator, and three flip-chip landing pads for the LiNbO3 resonator die.
Numbers (switch width, capacitor values) are read from results/design_final.json.

The layer map is generic (no foundry deck); DRC/LVS sign-off must be run in
the target PDK (see cadence/README.md).
"""
import os, json, math
import gdstk

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'layout')

# ------------------------------------------------------------------ layer map
L = dict(NWELL=(1, 0), ACTIVE=(2, 0), POLY=(3, 0), NIMP=(4, 0), PIMP=(5, 0), CONT=(6, 0),
         M1=(7, 0), VIA1=(8, 0), M2=(9, 0), VIA2=(10, 0), M3=(11, 0), VIA3=(12, 0), M4=(13, 0),
         M5=(15, 0), M8=(21, 0), MIM=(30, 0), VIA8=(22, 0), M9=(23, 0), PAD=(40, 0), TEXT=(63, 0), PRBND=(64, 0))

lib = gdstk.Library(unit=1e-6, precision=1e-9)


def rect(cell, layer, x0, y0, x1, y1):
    cell.add(gdstk.rectangle((x0, y0), (x1, y1), layer=L[layer][0], datatype=L[layer][1]))


def text(cell, s, x, y, size=2.0):
    cell.add(*gdstk.text(s, size, (x, y), layer=L['TEXT'][0], datatype=L['TEXT'][1]))


# ------------------------------------------------------------- transistor row
def mosfet(cell, x, y, w, l, nf, ptype=False, pitch=0.26):
    """Multi-finger MOSFET: poly fingers over active with contacted S/D. Returns (x_end, y_top)."""
    cw = 0.09  # contact size
    sd = 0.20  # S/D length
    length = nf * (l + sd) + sd
    rect(cell, 'ACTIVE', x, y, x + length, y + w)
    rect(cell, 'PIMP' if ptype else 'NIMP', x - 0.1, y - 0.1, x + length + 0.1, y + w + 0.1)
    if ptype:
        rect(cell, 'NWELL', x - 0.3, y - 0.3, x + length + 0.3, y + w + 0.3)
    xx = x
    for i in range(nf + 1):
        # S/D contacts
        ncont = max(1, int(w // pitch))
        for k in range(ncont):
            cy = y + 0.07 + k * pitch
            rect(cell, 'CONT', xx + (sd - cw) / 2, cy, xx + (sd + cw) / 2, cy + cw)
        rect(cell, 'M1', xx + 0.02, y - 0.05, xx + sd - 0.02, y + w + 0.05)
        xx += sd
        if i < nf:
            rect(cell, 'POLY', xx, y - 0.15, xx + l, y + w + 0.15)
            xx += l
    return x + length, y + w


def inverter(name, wn, wp, nf):
    c = lib.new_cell(name)
    mosfet(c, 0, 0, wn / nf, 0.065, nf, ptype=False)
    xe, _ = mosfet(c, 0, wn / nf + 0.6, wp / nf, 0.065, nf, ptype=True)
    # rails
    rect(c, 'M1', -0.2, -0.45, xe + 0.2, -0.15)              # VSS
    top = wn / nf + 0.6 + wp / nf
    rect(c, 'M1', -0.2, top + 0.15, xe + 0.2, top + 0.45)    # VDD
    rect(c, 'POLY', 0.2, wn / nf + 0.1, xe - 0.2, wn / nf + 0.5)  # gate strap
    return c, xe, top + 0.45


def dff(name):
    """A compact TG master-slave DFF with reset, drawn as a row of gates (24 transistors)."""
    c = lib.new_cell(name)
    x = 0.0
    for i in range(12):   # 6 inverters-equivalent + 4 TG + NAND ~ 12 pairs
        mosfet(c, x, 0.0, 0.4, 0.065, 1)
        mosfet(c, x, 1.0, 0.8, 0.065, 1, ptype=True)
        x += 0.65
    rect(c, 'M1', -0.2, -0.45, x + 0.2, -0.15)
    rect(c, 'M1', -0.2, 2.0, x + 0.2, 2.3)
    rect(c, 'M2', -0.2, 0.75, x + 0.2, 0.85)   # clk
    rect(c, 'M2', -0.2, 0.55, x + 0.2, 0.65)   # clkb
    rect(c, 'M2', -0.2, 0.35, x + 0.2, 0.45)   # rstn
    return c, x, 2.3


def switch_array(name, W_um, wf=5.0, nf_row=40):
    """Wide nMOS RF switch: W_um total, fingers of wf um in rows of nf_row (drain/source interdigitated, M2/M3 buses)."""
    c = lib.new_cell(name)
    nf = max(1, int(round(W_um / wf)))
    rows = max(1, int(math.ceil(nf / nf_row)))
    pitch_y = wf + 1.2
    xe = 0
    for k in range(rows):
        n_here = min(nf_row, nf - k * nf_row)
        xe = max(xe, mosfet(c, 0, k * pitch_y, wf, 0.065, n_here, ptype=False)[0])
    h = rows * pitch_y
    rect(c, 'M2', -0.3, -0.5, xe + 0.3, -0.2)          # source bus (star)
    rect(c, 'M2', -0.3, h - 0.9, xe + 0.3, h - 0.6)    # drain bus (to Csw)
    rect(c, 'M3', -0.5, -0.5, -0.2, h)                 # gate strap (poly contacted at both ends)
    rect(c, 'POLY', -0.2, -0.3, 0.0, h - 0.6)
    return c, xe + 0.5, h


def mim(name, cap_pF, density_fF_um2=2.0):
    c = lib.new_cell(name)
    side = math.sqrt(cap_pF * 1e3 / density_fF_um2)
    rect(c, 'M8', -0.5, -0.5, side + 0.5, side + 0.5)
    rect(c, 'MIM', 0, 0, side, side)
    rect(c, 'M9', 0.3, 0.3, side - 0.3, side - 0.3)
    n = max(1, int(side // 2))
    for i in range(n):
        for j in range(n):
            rect(c, 'VIA8', 1 + 2 * i, 1 + 2 * j, 1.4 + 2 * i, 1.4 + 2 * j)
    return c, side + 1


def pad(name, size=60.0, rf=False):
    c = lib.new_cell(name)
    rect(c, 'M9', 0, 0, size, size)
    rect(c, 'PAD', 4, 4, size - 4, size - 4)
    if rf:
        pass
    return c, size


def main():
    p = {}
    fp = os.path.join(ROOT, 'results', 'design_final.json')
    if os.path.exists(fp):
        p = json.load(open(fp))
    W = p.get('W_um', 1000.0)
    Csh = p.get('Cp', 3e-12) * 1e12
    Csw = p.get('Csw', 2e-12) * 1e12
    Cpar = p.get('Cpar', 0.0) * 1e12

    top = lib.new_cell('CIRCULATOR_DRIVER_TOP')
    DIE = 800.0
    rect(top, 'PRBND', 0, 0, DIE, DIE)
    text(top, 'STM ACOUSTIC CIRCULATOR CMOS DRIVER 65nm v1.0', 60, DIE - 95, 5)

    # ---- pads ----
    padc, ps = pad('PAD_DC')
    padrf, _ = pad('PAD_RF', rf=True)
    # RF GSG pads on left (port 1), right (port 2), bottom (port 3)
    gsg_positions = {
        'P1': [(20, 540), (20, 440), (20, 340)],
        'P2': [(DIE - 80, 540), (DIE - 80, 440), (DIE - 80, 340)],
        'P3': [(300, 20), (400, 20), (500, 20)],
    }
    for k, pts in gsg_positions.items():
        for i, (x, y) in enumerate(pts):
            top.add(gdstk.Reference(padrf if i == 1 else padc, (x, y)))
            text(top, ('G', k, 'G')[i], x + 25, y + 25, 5)
    # DC / clock pads along the top
    dc_names = ['VSS', 'VDD', 'VDD', 'VSS', 'CLK', 'RSTN', 'DIR', 'VSS']
    for i, nme in enumerate(dc_names):
        x = 45 + i * 102
        top.add(gdstk.Reference(padc, (x, DIE - 80)))
        text(top, nme, x + 8, DIE - 55, 5)

    # ---- resonator flip-chip landing pads (centre) ----
    rect(top, 'PRBND', 300, 300, 500, 500)
    for i, (x, y) in enumerate([(320, 420), (440, 420), (380, 320)]):
        rect(top, 'M9', x, y, x + 50, y + 50)
        rect(top, 'PAD', x + 8, y + 8, x + 42, y + 42)
        text(top, f'RES{i+1}', x + 8, y + 20, 4)
    text(top, 'LiNbO3 resonator die (flip-chip, 200 um)', 305, 505, 3.5)

    # ---- varactor arrays and drivers, one per resonator ----
    var, vw, vh = switch_array('NMOS_SWITCH', W)
    cpc, cpside = mim('MIM_CSW', Csw)
    ccc, ccside = mim('MIM_CSH', Csh)
    cds = 0.0
    inv_sizes = [(0.6, 1.2, 1), (1.8, 3.6, 2), (5.4, 10.8, 4), (16, 32, 8), (48, 96, 16)]
    invs = [inverter(f'INV_{i}', wn, wp, nf) for i, (wn, wp, nf) in enumerate(inv_sizes)]
    drv = lib.new_cell('VDRV')
    x = 0
    for c, xe, yt in invs:
        drv.add(gdstk.Reference(c, (x, 0)))
        x += xe + 1.5
    rect(drv, 'M3', -1, -1.5, x, -0.9)   # VSS strap
    rect(drv, 'M3', -1, 8.5, x, 9.1)     # VDDM strap
    drvw = x

    cells = lib.new_cell('CHANNEL')     # one modulation channel: driver -> switch gate; Csw (MIM) ; Csh (MIM) at the port
    cells.add(gdstk.Reference(drv, (0, 0)))
    cells.add(gdstk.Reference(var, (drvw + 8, 0)))
    cells.add(gdstk.Reference(cpc, (drvw + vw + 16, 0)))            # Csw
    cells.add(gdstk.Reference(ccc, (drvw + vw + 16, cpside + 6)))   # Csh
    rect(cells, 'M4', drvw - 1, 3.5, drvw + 8, 4.5)                 # gate drive routing
    rect(cells, 'M4', drvw + vw + 8, vh - 1.5, drvw + vw + 16, vh - 0.5)   # drain -> Csw
    chan_w = drvw + vw + 16 + cpside + 6

    places = [(120, 430, 0), (DIE - 120, 470, math.pi), (440, 110, math.pi / 2)]
    for i, (x, y, rot) in enumerate(places):
        top.add(gdstk.Reference(cells, (x, y), rotation=rot))
        text(top, f'CH{i+1}', x - 10, y - 45 if rot == 0 else (y + 30 if rot == math.pi else y - 10), 5)
    # RF routing (M9, 10 um) from signal pads to the port capacitors of each channel
    rect(top, 'M9', 80, 465, 120, 475)                     # P1 pad -> CH1 input
    rect(top, 'M9', DIE - 120, 465, DIE - 80, 475)         # P2 pad -> CH2
    rect(top, 'M9', 445, 80, 455, 110)                     # P3 pad -> CH3
    # tank nodes -> resonator landing pads (M9)
    rect(top, 'M9', 120 + chan_w, 445, 320, 455)
    rect(top, 'M9', 490, 445, DIE - 120 - chan_w, 455)
    rect(top, 'M9', 400, 110 + chan_w, 410, 320)

    # ---- phase generator (3 DFFs + buffers) ----
    pg = lib.new_cell('PHASEGEN')
    dcell, dw, dh = dff('DFF_RN')
    for i in range(3):
        pg.add(gdstk.Reference(dcell, (i * (dw + 2), 0)))
    for i, (c, xe, yt) in enumerate(invs[:2] * 3):
        pg.add(gdstk.Reference(c, (i * 4, dh + 2)))
    rect(pg, 'M3', -1, -1, 3 * (dw + 2), -0.5)
    rect(pg, 'M3', -1, dh + 8, 3 * (dw + 2), dh + 8.5)
    top.add(gdstk.Reference(pg, (560, 560)))
    text(top, 'PHASE GEN (div-6 Johnson)', 540, 545, 3.5)

    # ---- global routing: VDD/VSS rings, clock, mod buses (M5) ----
    for off in (90, 96):
        rect(top, 'M5', off, off, DIE - off, off + 3)
        rect(top, 'M5', off, DIE - off - 3, DIE - off, DIE - off)
        rect(top, 'M5', off, off, off + 3, DIE - off)
        rect(top, 'M5', DIE - off - 3, off, DIE - off, DIE - off)
    text(top, 'VDD/VSS rings', 110, 112, 3)
    # modulation phase lines
    for i, y in enumerate((555, 551, 547)):
        rect(top, 'M4', 100, y, 620, y + 2)          # PH0/PH120/PH240 distribution
    rect(top, 'M4', 100, 440, 102, 557)
    rect(top, 'M4', DIE - 102, 480, DIE - 100, 557)
    rect(top, 'M4', 620, 480, 622, 557); rect(top, 'M4', 560, 120, 562, 547)
    # seal ring
    rect(top, 'M1', 2, 2, DIE - 2, 6); rect(top, 'M1', 2, DIE - 6, DIE - 2, DIE - 2)
    rect(top, 'M1', 2, 2, 6, DIE - 2); rect(top, 'M1', DIE - 6, 2, DIE - 2, DIE - 2)

    gds = os.path.join(OUT, 'circulator_driver_top.gds')
    lib.write_gds(gds)
    # stats
    area = DIE * DIE * 1e-6
    bb = cells.bounding_box()
    stats = dict(die_mm2=area, core_channel_um=[bb[1][0] - bb[0][0], bb[1][1] - bb[0][1]],
                 switch_W_um=W, Csw_pF=Csw, Csh_pF=Csh, Cpar_pF=Cpar, cells=len(lib.cells), gds=gds)
    json.dump(stats, open(os.path.join(OUT, 'layout_stats.json'), 'w'), indent=1)
    print(json.dumps(stats, indent=1))


if __name__ == '__main__':
    main()

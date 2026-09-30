#!/usr/bin/env python3
"""
gen_gaa_inverter_gds.py
-----------------------
Generates the GDSII stream file of a gate-all-around (GAA) nanosheet CMOS
inverter standard cell (INV_GAA_X1) with a dependency-free GDSII writer,
plus an SVG rendering of the same polygons and a JSON dump for documentation.

The geometry follows a generic 3-nm-class nanosheet design-rule set
(contacted gate pitch 48 nm, Lg 14 nm, 3 stacked sheets, 6-track cell,
M1 pitch 28 nm). Layer numbers follow the tech-file `gaa3.layermap`
shipped next to this script and used by the Innovus stream-out step.

Usage:
    python3 gen_gaa_inverter_gds.py            # writes gaa_inverter.gds, .svg, .json

The output can be read by Cadence Virtuoso (File > Import > Stream),
KLayout, or gdstk.  Database unit = 1 nm, user unit = 1 um.
"""
import json
import math
import struct
import time

# ----------------------------------------------------------------------------
# 1. Minimal GDSII stream writer (Calma GDSII Stream Format, release 6)
# ----------------------------------------------------------------------------
HEADER, BGNLIB, LIBNAME, UNITS, ENDLIB, BGNSTR, STRNAME, ENDSTR = (
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07)
BOUNDARY, PATH, SREF, TEXT, LAYER, DATATYPE, XY, ENDEL = (
    0x08, 0x09, 0x0A, 0x0C, 0x0D, 0x0E, 0x10, 0x11)
SNAME, TEXTTYPE, PRESENTATION, STRING, MAG, STRANS, ANGLE = 0x12, 0x16, 0x17, 0x19, 0x1B, 0x1A, 0x1C
WIDTH = 0x0F

DT_NONE, DT_BITARRAY, DT_INT2, DT_INT4, DT_REAL8, DT_ASCII = 0, 1, 2, 3, 5, 6


def _real8(value: float) -> bytes:
    """Encode a float as GDSII 8-byte excess-64 base-16 real."""
    if value == 0.0:
        return b"\x00" * 8
    sign = 0
    if value < 0:
        sign = 0x80
        value = -value
    exponent = 0
    while value >= 1.0:
        value /= 16.0
        exponent += 1
    while value < 1.0 / 16.0:
        value *= 16.0
        exponent -= 1
    mantissa = int(round(value * (1 << 56)))
    if mantissa >= (1 << 56):          # rounding overflow guard
        mantissa >>= 4
        exponent += 1
    return bytes([sign | (exponent + 64)]) + mantissa.to_bytes(7, "big")


def _record(rtype: int, dtype: int, payload: bytes = b"") -> bytes:
    length = 4 + len(payload)
    return struct.pack(">HBB", length, rtype, dtype) + payload


def _ascii(rtype: int, text: str) -> bytes:
    data = text.encode("ascii")
    if len(data) % 2:
        data += b"\x00"
    return _record(rtype, DT_ASCII, data)


def _int2(rtype: int, *values: int) -> bytes:
    return _record(rtype, DT_INT2, struct.pack(">%dh" % len(values), *values))


def _timestamp() -> bytes:
    t = time.localtime()
    stamp = (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
    return struct.pack(">12h", *(stamp + stamp))


class GdsLibrary:
    def __init__(self, name: str, user_unit=1e-6, db_unit=1e-9):
        self.name = name
        self.user_unit = user_unit
        self.db_unit = db_unit
        self.cells = []

    def write(self, path: str) -> None:
        out = bytearray()
        out += _int2(HEADER, 600)
        out += _record(BGNLIB, DT_INT2, _timestamp())
        out += _ascii(LIBNAME, self.name)
        out += _record(UNITS, DT_REAL8,
                       _real8(self.db_unit / self.user_unit) + _real8(self.db_unit))
        for cell in self.cells:
            out += cell.to_bytes()
        out += _record(ENDLIB, DT_NONE)
        with open(path, "wb") as fh:
            fh.write(out)


class GdsCell:
    def __init__(self, name: str):
        self.name = name
        self.polygons = []   # (layer, datatype, [(x, y), ...], tag)
        self.labels = []     # (layer, texttype, (x, y), string)
        self.refs = []       # (cellname, (x, y))

    def rect(self, layer, datatype, x0, y0, x1, y1, tag=""):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        self.polygons.append((layer, datatype, pts, tag))

    def label(self, layer, texttype, x, y, text):
        self.labels.append((layer, texttype, (x, y), text))

    def ref(self, cellname, x, y, mirror_x=False):
        """mirror_x: reflect about the y axis (GDS STRANS reflection + 180 deg) -- cell spans x-w..x when mirrored"""
        self.refs.append((cellname, (x, y), mirror_x))

    def to_bytes(self) -> bytes:
        out = bytearray()
        out += _record(BGNSTR, DT_INT2, _timestamp())
        out += _ascii(STRNAME, self.name)
        for layer, datatype, pts, _tag in self.polygons:
            out += _record(BOUNDARY, DT_NONE)
            out += _int2(LAYER, layer)
            out += _int2(DATATYPE, datatype)
            closed = list(pts) + [pts[0]]
            flat = [int(round(c)) for p in closed for c in p]
            out += _record(XY, DT_INT4, struct.pack(">%di" % len(flat), *flat))
            out += _record(ENDEL, DT_NONE)
        for layer, texttype, (x, y), text in self.labels:
            out += _record(TEXT, DT_NONE)
            out += _int2(LAYER, layer)
            out += _int2(TEXTTYPE, texttype)
            out += _record(PRESENTATION, DT_BITARRAY, struct.pack(">H", 0x0005))  # centre/centre
            out += _record(MAG, DT_REAL8, _real8(0.02))
            out += _record(XY, DT_INT4, struct.pack(">2i", int(x), int(y)))
            out += _ascii(STRING, text)
            out += _record(ENDEL, DT_NONE)
        for cellname, (x, y), *flags in self.refs:
            out += _record(SREF, DT_NONE)
            out += _ascii(SNAME, cellname)
            if flags and flags[0]:
                out += _record(STRANS, DT_BITARRAY, struct.pack(">H", 0x8000))
                out += _record(ANGLE, DT_REAL8, _real8(180.0))
            out += _record(XY, DT_INT4, struct.pack(">2i", int(x), int(y)))
            out += _record(ENDEL, DT_NONE)
        out += _record(ENDSTR, DT_NONE)
        return bytes(out)


# ----------------------------------------------------------------------------
# 2. Technology: generic 3-nm-class GAA nanosheet rules (nm)
# ----------------------------------------------------------------------------
TECH = dict(
    CPP=48,          # contacted poly (gate) pitch
    LG=14,           # physical gate length
    M1_PITCH=28,     # metal-1 pitch (6-track cell)
    TRACKS=6,
    NS_W_N=30,       # nanosheet width, NMOS
    NS_W_P=45,       # nanosheet width, PMOS (tuned for beta ratio)
    NS_T=5,          # nanosheet thickness
    NS_N=3,          # sheets in the stack
    NS_SPACE=9,      # vertical sheet-to-sheet spacing (inner spacer / gate fill)
    SD_W=20,         # source/drain trench contact width
    V0=10,           # via-0 size
    M1_W=16,         # metal-1 line width
    RAIL_W=24,       # power rail width (straddles cell boundary)
)
CELL_H = TECH["TRACKS"] * TECH["M1_PITCH"]      # 168 nm
CELL_W = 2 * TECH["CPP"]                       # 96 nm (single-gate cell + 2 half dummy gates)

# GDS layer map (layer, datatype) -- see gaa3.layermap
L = dict(
    NWELL=(1, 0), NSHEET=(2, 0), NS_STACK_MARK=(2, 1), GATE=(3, 0), GATE_CUT=(3, 1),
    SDC=(4, 0), CB=(5, 0), V0=(6, 0), M1=(7, 0), M1_PIN=(7, 1), M1_TEXT=(7, 2),
    PRBOUND=(235, 0),
)


def build_inverter() -> GdsCell:
    t = TECH
    c = GdsCell("INV_GAA_X1")
    xc = CELL_W // 2                      # gate centre
    lg2 = t["LG"] // 2

    # -- boundary and wells ----------------------------------------------------
    c.rect(*L["PRBOUND"], 0, 0, CELL_W, CELL_H, "prBoundary")
    c.rect(*L["NWELL"], 0, CELL_H // 2, CELL_W, CELL_H, "NWELL")

    # -- nanosheet stacks (active) ---------------------------------------------
    n_y0, n_y1 = 34, 34 + t["NS_W_N"]                      # NMOS sheet band (34..64)
    p_y1 = CELL_H - 34
    p_y0 = p_y1 - t["NS_W_P"]                              # PMOS sheet band (89..134)
    act_x0, act_x1 = 8, CELL_W - 8
    c.rect(*L["NSHEET"], act_x0, n_y0, act_x1, n_y1, "NS_N")
    c.rect(*L["NSHEET"], act_x0, p_y0, act_x1, p_y1, "NS_P")
    # stack-count marker (3 sheets) drawn as thin stripes for visualisation
    for i in range(t["NS_N"]):
        dy_n = n_y0 + 4 + i * ((t["NS_W_N"] - 8) // t["NS_N"])
        dy_p = p_y0 + 5 + i * ((t["NS_W_P"] - 10) // t["NS_N"])
        c.rect(*L["NS_STACK_MARK"], act_x0 + 2, dy_n, act_x1 - 2, dy_n + 2, "sheet")
        c.rect(*L["NS_STACK_MARK"], act_x0 + 2, dy_p, act_x1 - 2, dy_p + 2, "sheet")

    # -- gates: active gate + two half dummy (diffusion-break) gates -------------
    c.rect(*L["GATE"], xc - lg2, 14, xc + lg2, CELL_H - 14, "gate")
    c.rect(*L["GATE"], -lg2, 14, lg2, CELL_H - 14, "dummy")
    c.rect(*L["GATE"], CELL_W - lg2, 14, CELL_W + lg2, CELL_H - 14, "dummy")
    c.rect(*L["GATE_CUT"], 0, CELL_H // 2 - 4, CELL_W, CELL_H // 2 + 4, "cut (N/P share gate: no cut on active gate)")

    # -- source/drain trench contacts -----------------------------------------
    sd = t["SD_W"]
    src_x0 = xc - lg2 - 4 - sd          # 14..34
    drn_x0 = xc + lg2 + 10              # 65..85 (output bar 12 nm from the input pad)
    for (y0, y1) in ((n_y0 - 2, n_y1 + 2), (p_y0 - 2, p_y1 + 2)):
        c.rect(*L["SDC"], src_x0, y0, src_x0 + sd, y1, "S")
        c.rect(*L["SDC"], drn_x0, y0, drn_x0 + sd, y1, "D")

    # -- gate contact (CB) in the mid region between N and P sheets --------------
    c.rect(*L["CB"], xc - lg2 - 2, CELL_H // 2 - 8, xc + lg2 + 2, CELL_H // 2 + 8, "CB")

    # -- metal-1 -----------------------------------------------------------------
    m1 = t["M1_W"]
    rw = t["RAIL_W"] // 2
    c.rect(*L["M1"], -4, -rw, CELL_W + 4, rw, "VSS rail")
    c.rect(*L["M1"], -4, CELL_H - rw, CELL_W + 4, CELL_H + rw, "VDD rail")
    # source straps to rails
    sx = src_x0 + sd // 2
    c.rect(*L["M1"], sx - m1 // 2, 0, sx + m1 // 2, n_y1, "VSS strap")
    c.rect(*L["M1"], sx - m1 // 2, CELL_H // 2 + 20, sx + m1 // 2, CELL_H, "VDD strap")   # starts 12 nm above the A pad
    # output: vertical M1 joining N and P drains
    dx = drn_x0 + sd // 2
    c.rect(*L["M1"], dx - m1 // 2, n_y0, dx + m1 // 2, p_y1, "Y")
    c.rect(*L["M1_PIN"], dx - m1 // 2, CELL_H // 2 - 8, dx + m1 // 2, CELL_H // 2 + 8, "Y pin")
    # input: M1 landing pad over gate contact
    c.rect(*L["M1"], xc - 9, CELL_H // 2 - 8, xc + 7, CELL_H // 2 + 8, "A")            # 16-nm pad, 12 nm from the Y bar
    c.rect(*L["M1_PIN"], xc - 9, CELL_H // 2 - 8, xc + 7, CELL_H // 2 + 8, "A pin")

    # -- via-0 --------------------------------------------------------------------
    v = t["V0"] // 2
    for (x, y) in ((sx, (n_y0 + n_y1) // 2), (sx, (p_y0 + p_y1) // 2 + 1),   # P source via 1 nm up: enclosed by the shortened strap
                   (dx, (n_y0 + n_y1) // 2), (dx, (p_y0 + p_y1) // 2),
                   (xc - 1, CELL_H // 2)):
        c.rect(*L["V0"], x - v, y - v, x + v, y + v, "V0")

    # -- pin labels ---------------------------------------------------------------
    c.label(*L["M1_TEXT"], xc - 1, CELL_H // 2, "A")
    c.label(*L["M1_TEXT"], dx, CELL_H // 2, "Y")
    c.label(*L["M1_TEXT"], CELL_W // 2, CELL_H, "VDD")
    c.label(*L["M1_TEXT"], CELL_W // 2, 0, "VSS")
    return c


# ----------------------------------------------------------------------------
# 3. SVG renderer (same polygons, GDS-viewer style)
# ----------------------------------------------------------------------------
STYLE = {  # layer -> (fill, stroke, opacity)
    (235, 0): ("none", "#8a8f98", 1.0),
    (1, 0): ("#c9b458", "#a08b2e", 0.22),
    (2, 0): ("#4caf50", "#2e7d32", 0.55),
    (2, 1): ("#1b5e20", "#1b5e20", 0.9),
    (3, 0): ("#e53935", "#b71c1c", 0.75),
    (3, 1): ("none", "#b71c1c", 0.9),
    (4, 0): ("#9e9e9e", "#616161", 0.9),
    (5, 0): ("#212121", "#000000", 0.9),
    (6, 0): ("#ffffff", "#000000", 1.0),
    (7, 0): ("#1e88e5", "#0d47a1", 0.62),
    (7, 1): ("none", "#0d47a1", 1.0),
}


def to_svg(cell: GdsCell, pad=20, scale=3.0) -> str:
    xs = [p[0] for _, _, pts, _ in cell.polygons for p in pts]
    ys = [p[1] for _, _, pts, _ in cell.polygons for p in pts]
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    w, h = (x1 - x0) * scale, (y1 - y0) * scale

    def X(x): return (x - x0) * scale
    def Y(y): return (y1 - y) * scale  # flip: GDS y up, SVG y down

    order = [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0), (5, 0), (7, 0), (6, 0), (7, 1), (235, 0)]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
             f'width="{w:.0f}" height="{h:.0f}" font-family="ui-monospace, monospace">']
    parts.append('<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" '
                 'patternTransform="rotate(45)"><rect width="6" height="6" fill="#e53935" opacity="0.35"/>'
                 '<line x1="0" y1="0" x2="0" y2="6" stroke="#b71c1c" stroke-width="1.5"/></pattern></defs>')
    for key in order:
        for layer, dt, pts, tag in cell.polygons:
            if (layer, dt) != key:
                continue
            fill, stroke, op = STYLE[key]
            if key == (3, 0):
                fill = "url(#hatch)"
            d = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in pts)
            dash = ' stroke-dasharray="4 3"' if key in ((235, 0), (3, 1), (7, 1)) else ""
            parts.append(f'<polygon points="{d}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" '
                         f'stroke-width="1"{dash}><title>L{layer}:{dt} {tag}</title></polygon>')
    for layer, tt, (x, y), text in cell.labels:
        parts.append(f'<text x="{X(x):.1f}" y="{Y(y) + 4:.1f}" text-anchor="middle" font-size="12" '
                     f'font-weight="700" fill="#111">{text}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    lib = GdsLibrary("GAA3_INV_LIB")
    inv = build_inverter()
    lib.cells.append(inv)
    lib.write("gaa_inverter.gds")
    with open("gaa_inverter.svg", "w") as fh:
        fh.write(to_svg(inv))
    with open("gaa_inverter_polygons.json", "w") as fh:
        json.dump(dict(tech=TECH, cell_w_nm=CELL_W, cell_h_nm=CELL_H,
                       polygons=[dict(layer=l, datatype=d, tag=t, xy=p) for l, d, p, t in inv.polygons],
                       labels=[dict(layer=l, texttype=t, xy=xy, text=s) for l, t, xy, s in inv.labels]),
                  fh, indent=1)
    n_poly = len(inv.polygons)
    print(f"wrote gaa_inverter.gds  cell {inv.name}  {CELL_W}x{CELL_H} nm  {n_poly} polygons  "
          f"{len(inv.labels)} labels  area {CELL_W*CELL_H/1e6:.4f} um^2")

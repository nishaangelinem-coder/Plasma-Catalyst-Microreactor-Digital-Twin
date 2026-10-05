#!/usr/bin/env python3
"""
make_schematics.py — publication-quality schematics (schemdraw) and the CFET stack cartoon
(matplotlib) for the UCM-CFET multi-material paper.

Outputs (SVG + PNG at 300 dpi in schematics/, PNG in figures/):
  schematics/tb_device.{svg,png}   single 4-terminal FET test bench (VGS, VDS, I(VDS))
  schematics/inv_cfet.{svg,png}    CMOS inverter drawn as a CFET with parasitics
  schematics/tb_inv.{svg,png}      inverter test bench (VDD, vpulse VIN, CLOAD)
  schematics/ro5_cfet.{svg,png}    5-stage ring oscillator, probe n3, I(VDD) meter
  figures/fig01_cfet_stacks.png    cross-section cartoons of the five CFET platforms

Run:  python3 schematics/make_schematics.py
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import schemdraw
import schemdraw.elements as elm
import schemdraw.logic as logic
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG_DIR = os.path.join(ROOT, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

SANS = ["Arial", "Helvetica", "Liberation Sans", "Nimbus Sans", "DejaVu Sans"]
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": SANS, "font.size": 8,
    "axes.titlesize": 9, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "svg.fonttype": "none", "pdf.fonttype": 42,
    "mathtext.fontset": "custom", "mathtext.rm": "sans", "mathtext.it": "sans:italic",
})

# Okabe-Ito colour-blind-safe palette
C = dict(blue="#0072B2", orange="#E69F00", sky="#56B4E9", green="#009E73", yellow="#F0E442",
         vermilion="#D55E00", purple="#CC79A7", black="#000000", grey="#7F7F7F")
COL_N = C["blue"]          # n-tier / n-FET
COL_P = C["vermilion"]     # p-tier / p-FET
COL_G = C["orange"]        # gate
COL_PAR = C["purple"]      # parasitics
COL_SRC = C["green"]       # sources / meters

schemdraw.use("matplotlib")
FS = 8  # pt


def new_drawing():
    d = schemdraw.Drawing(show=False)
    d.config(fontsize=FS, font="sans-serif", unit=2.5, lw=1.1, inches_per_unit=0.42)
    return d


def save(d: schemdraw.Drawing, name: str):
    svg = os.path.join(HERE, f"{name}.svg")
    png = os.path.join(HERE, f"{name}.png")
    d.save(svg, transparent=False)
    d.save(png, transparent=False, dpi=300)
    print(f"wrote {os.path.relpath(svg, ROOT)}, {os.path.relpath(png, ROOT)}")


# ----------------------------------------------------------------------------- helpers
def text(d, xy, s, **kw):
    """Free text at absolute position (halign/valign via kw)."""
    kw.setdefault("fontsize", FS)
    d.add(elm.Label().at(xy).label(s, **kw))


def dashed_box(d, x0, y0, x1, y1, color):
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        d.add(elm.Line().at(a).to(b).linestyle("--").linewidth(0.8).color(color))


def caption(d, s):
    bb = d.get_bbox()
    text(d, ((bb.xmin + bb.xmax) / 2, bb.ymin - 0.7), s, fontsize=FS - 0.5)


# ----------------------------------------------------------------------------- 1. tb_device
def tb_device():
    d = new_drawing()
    # DUT: generic GAA n-FET, 4 terminals d g s b (gate on the left, drain on top)
    fet = d.add(elm.NFet(bulk=True).reverse().at((0, 0)).color(COL_N))
    text(d, (0.55, -0.75), "gaa_n\n(DUT)", color=COL_N, halign="left")
    text(d, (0.15, 0.05), "d", halign="left")
    text(d, (0.15, -1.65), "s", halign="left")
    text(d, (fet.gate.x - 0.15, -0.55), "g", halign="right")
    text(d, (1.35, -0.75), "b", halign="left")
    # body tied to source
    d.add(elm.Line().at(fet.bulk).right(1.1).color(COL_N))
    d.add(elm.Line().down(1.2).color(COL_N))
    d.add(elm.Line().left().tox(fet.source).color(COL_N))
    d.add(elm.Dot().at(fet.source))
    d.add(elm.Line().at(fet.source).down(1.0))
    gnd = d.add(elm.Ground())
    y_gnd = gnd.start.y
    # drain: ammeter + VDS source
    d.add(elm.Line().at(fet.drain).up(0.5))
    d.add(elm.MeterI().up(2.0).label("I(VDS)", loc="bottom", ofst=0.2).color(COL_SRC))
    d.add(elm.Line().up(0.4))
    d.add(elm.Line().right(3.0))
    d.add(elm.SourceV().down(2.4).label("VDS", loc="top", ofst=0.2).color(COL_SRC).reverse())
    d.add(elm.Line().down().toy(y_gnd))
    d.add(elm.Ground())
    # gate: VGS source
    d.add(elm.Line().at(fet.gate).left(1.4))
    d.add(elm.SourceV().down(2.4).label("VGS", loc="bottom", ofst=0.2).color(COL_SRC).reverse())
    d.add(elm.Line().down().toy(y_gnd))
    d.add(elm.Ground())
    caption(d, "tb_device: DC sweep of VGS and VDS; I_D = I(VDS); body tied to source (ground)")
    save(d, "tb_device")


# ----------------------------------------------------------------------------- 2. inv_cfet
def inv_cfet():
    d = new_drawing()
    x0 = 0.0
    yp, yn = 5.2, 0.0          # drain y of p-FET (top) and n-FET (bottom)
    pf = d.add(elm.PFet(bulk=True).reverse().at((x0, yp)).color(COL_P))    # source top, drain bottom
    nf = d.add(elm.NFet(bulk=True).reverse().at((x0, yn)).color(COL_N))    # drain top, source bottom
    text(d, (x0 + 0.5, pf.center.y + 0.1), "p-FET\n(tier 2)", color=COL_P, halign="left")
    text(d, (x0 + 0.5, nf.center.y + 0.1), "n-FET\n(tier 1)", color=COL_N, halign="left")
    # bodies tied to sources
    d.add(elm.Line().at(pf.bulk).right(1.0).color(COL_P)); d.add(elm.Line().up().toy(pf.source).color(COL_P)); d.add(elm.Line().left().tox(pf.source).color(COL_P))
    d.add(elm.Line().at(nf.bulk).right(1.0).color(COL_N)); d.add(elm.Line().down().toy(nf.source).color(COL_N)); d.add(elm.Line().left().tox(nf.source).color(COL_N))
    # common vertical gate
    gx = pf.gate.x
    ym = (pf.gate.y + nf.gate.y) / 2
    d.add(elm.Line().at(pf.gate).down().toy(nf.gate).color(COL_G).linewidth(2.4))
    d.add(elm.Dot().at((gx, ym)))
    d.add(elm.Line().at((gx, ym)).left(1.6).color(COL_G).linewidth(2.4))
    d.add(elm.Dot(open=True).label("in", loc="left"))
    text(d, (gx - 0.15, ym + 0.9), "common\nvertical\ngate", color=COL_G, halign="right", fontsize=FS - 1)
    # supplies
    d.add(elm.Dot().at(pf.source)); d.add(elm.Line().at(pf.source).up(0.5)); d.add(elm.Vdd().label("vdd"))
    d.add(elm.Dot().at(nf.source)); d.add(elm.Line().at(nf.source).down(0.5)); d.add(elm.Vss().label("vss"))
    # drain legs with local resistances (tier-local S/D + via resistance)
    d.add(elm.Dot().at(pf.drain)); d.add(elm.Dot().at(nf.drain))
    rp = d.add(elm.Resistor().at(pf.drain).down(1.3).label("Rlocal_p", loc="bottom", ofst=0.15, color=COL_PAR).color(COL_PAR))
    rn = d.add(elm.Resistor().at(nf.drain).up(1.3).label("Rlocal_n", loc="top", ofst=0.15, color=COL_PAR).color(COL_PAR))
    yo = (rp.end.y + rn.end.y) / 2
    d.add(elm.Line().at(rp.end).down().toy(yo))
    d.add(elm.Line().at(rn.end).up().toy(yo))
    d.add(elm.Dot().at((x0, yo)))
    d.add(elm.Line().at((x0, yo)).right(4.2))
    d.add(elm.Dot(open=True).label("out", loc="right"))
    # Cstack: capacitance between the p and n drain nodes across the inter-tier dielectric
    xc = x0 + 2.0
    d.add(elm.Line().at(pf.drain).right(xc - x0).color(COL_PAR))
    d.add(elm.Capacitor().at((xc, pf.drain.y)).down().toy(nf.drain).color(COL_PAR))
    d.add(elm.Line().left().tox(nf.drain).color(COL_PAR))
    text(d, (xc + 0.25, yo + 0.75), "Cstack\n(inter-tier)", color=COL_PAR, halign="left", valign="bottom")
    # Cout from out to vss
    xo = x0 + 3.4
    d.add(elm.Dot().at((xo, yo)))
    d.add(elm.Capacitor().at((xo, yo)).down(1.7).label("Cout", loc="top", ofst=0.15, color=COL_PAR).color(COL_PAR))
    d.add(elm.Vss().label("vss"))
    # tier boxes (absolute coordinates)
    dashed_box(d, x0 - 1.75, pf.drain.y - 0.3, x0 + 1.6, pf.source.y + 0.3, COL_P)
    dashed_box(d, x0 - 1.75, nf.source.y - 0.3, x0 + 1.6, nf.drain.y + 0.3, COL_N)
    text(d, (x0 + 1.55, pf.source.y + 0.68), "tier 2 (top): p", color=COL_P, halign="right", fontsize=FS - 1)
    text(d, (x0 + 1.55, nf.source.y - 0.7), "tier 1 (bottom): n", color=COL_N, halign="right", fontsize=FS - 1)
    caption(d, "inv_cfet: p-FET stacked over n-FET on one vertical gate; parasitics Rlocal_n/p, Cstack, Cout")
    save(d, "inv_cfet")


# ----------------------------------------------------------------------------- 3. tb_inv
def tb_inv():
    d = new_drawing()
    inv = d.add(logic.Not().at((0, 0)))
    text(d, (inv.center.x - 0.1, 0.75), "inv_cfet", halign="right")
    # power pins on the symbol
    d.add(elm.Line().at(inv.center).up(0.9)); d.add(elm.Vdd().label("vdd"))
    d.add(elm.Line().at(inv.center).down(0.9)); d.add(elm.Vss().label("vss"))
    # input pulse
    d.add(elm.Line().at(inv.in1).left(0.6))
    d.add(elm.Dot().label("in", loc="top", ofst=0.1))
    d.add(elm.Line().left(1.4))
    d.add(elm.SourcePulse().down(2.4).label("VIN\n(vpulse)", loc="bottom", ofst=0.25).color(COL_SRC).reverse())
    gnd = d.add(elm.Ground())
    y_gnd = gnd.start.y
    # output load
    d.add(elm.Line().at(inv.out).right(1.4))
    d.add(elm.Dot().label("out", loc="top", ofst=0.1))
    d.add(elm.Line().down(0.4))
    d.add(elm.Capacitor().down().toy(y_gnd).label("CLOAD", loc="top", ofst=0.2, color=COL_PAR).color(COL_PAR))
    d.add(elm.Ground())
    # VDD supply
    xv = inv.out.x + 3.6
    d.add(elm.Line().at((xv, 0.6)).up(0.4)); d.add(elm.Vdd().label("vdd"))
    d.add(elm.SourceV().at((xv, 0.6)).down().toy(y_gnd).label("VDD", loc="top", ofst=0.2).color(COL_SRC).reverse())
    d.add(elm.Ground())
    caption(d, "tb_inv: transient; VIN pulse -> in, out loaded by CLOAD; VDD supply, vss = 0")
    save(d, "tb_inv")


# ----------------------------------------------------------------------------- 4. ro5_cfet
def ro5_cfet():
    d = new_drawing()
    d.config(unit=2.0)
    n = 5
    invs = []
    x = 0.0
    pitch = 3.2
    for k in range(n):
        inv = d.add(logic.Not().at((x, 0)))
        invs.append(inv)
        text(d, (inv.center.x - 0.5, -0.7), f"I{k+1}", halign="right")
        if k < n - 1:
            d.add(elm.Line().at(inv.out).tox(x + pitch + 1.05))
            nd = d.add(elm.Dot().at((inv.out.x + (pitch - 0.9) / 2, 0)))
            text(d, (nd.center.x, -0.28), f"n{k+1}", valign="top")
        x += pitch
    # power rails: each inverter symbol has vdd/vss ticks
    y_vdd, y_vss = 1.9, -1.9
    for inv in invs:
        d.add(elm.Line().at(inv.center).up().toy(y_vdd)); d.add(elm.Dot().at((inv.center.x, y_vdd)))
        d.add(elm.Line().at(inv.center).down().toy(y_vss)); d.add(elm.Dot().at((inv.center.x, y_vss)))
    xl, xr = invs[0].center.x - 1.6, invs[-1].out.x + 1.6
    d.add(elm.Line().at((xl, y_vdd)).to((xr, y_vdd)))
    d.add(elm.Line().at((xl, y_vss)).to((xr, y_vss)))
    text(d, (xl - 0.15, y_vdd), "vdd", halign="right")
    text(d, (xl - 0.15, y_vss), "vss", halign="right")
    # feedback wire: out of I5 -> in of I1 (node n5)
    y_fb = -3.1
    d.add(elm.Line().at(invs[-1].out).right(0.8))
    d.add(elm.Dot())
    text(d, (invs[-1].out.x + 0.8, -0.28), "n5", valign="top")
    d.add(elm.Line().down().toy(y_fb))
    d.add(elm.Line().left().tox(invs[0].in1.x - 0.8))
    d.add(elm.Line().up().toy(0))
    d.add(elm.Line().right().to(invs[0].in1))
    text(d, (invs[2].center.x, y_fb - 0.3), "feedback: n5 -> I1 input", valign="top", fontsize=FS - 1)
    # probe at n3
    px = invs[2].out.x + (pitch - 0.9) / 2
    d.add(elm.Line().at((px, 0)).up(0.9).linestyle("--").color(COL_SRC))
    d.add(elm.Dot(open=True).color(COL_SRC))
    text(d, (px, 1.15), "probe V(n3)", color=COL_SRC, valign="bottom", fontsize=FS - 1)
    # VDD supply through ammeter I(VDD)
    vx = xr + 0.9
    d.add(elm.Line().at((xr, y_vdd)).to((vx, y_vdd)))
    d.add(elm.Line().at((vx, y_vdd)).up(0.8))
    d.add(elm.MeterI().right(1.8).label("I(VDD)", loc="top", ofst=0.2).color(COL_SRC))
    d.add(elm.Line().right(0.3))
    d.add(elm.SourceV().down().toy(y_vss).label("VDD", loc="top", ofst=0.2).color(COL_SRC).reverse())
    d.add(elm.Line().left().tox(xr))
    d.add(elm.Ground().at((xr + 1.0, y_vss)))
    caption(d, "ro5_cfet: 5-stage CFET inverter ring; f_RO from V(n3); P = VDD x <I(VDD)>")
    save(d, "ro5_cfet")


# ----------------------------------------------------------------------------- 5. CFET stack cartoon
def cfet_stacks():
    platforms = [
        ("Si", "Si nanosheet n / Si nanosheet p", "advanced-node", "ns", "ns", COL_N, COL_P),
        ("SiGe", "Si nanosheet n / SiGe nanosheet p", "advanced-node", "ns", "ns_sige", COL_N, COL_P),
        ("TMD", "MoS$_2$ monolayer n / WSe$_2$ monolayer p", "emerging post-Si", "2d", "2d", COL_N, COL_P),
        ("CNT", "aligned CNT array n / p", "emerging post-Si", "cnt", "cnt", COL_N, COL_P),
        ("GaN", "AlGaN/GaN 2DEG n / p-GaN p", "exploratory / projected", "2deg", "pgan", COL_N, COL_P),
    ]
    fig, axes = plt.subplots(1, 5, figsize=(7.16, 2.45))
    col_sub, col_ox, col_gate, col_ct, col_ild = "#BDBDBD", "#E8E8E8", COL_G, "#4D4D4D", "#F5F0E1"
    for i, (ax, (name, chan, tag, kb, kt, cn, cp)) in enumerate(zip(axes, platforms)):
        ax.set_xlim(0, 10); ax.set_ylim(-0.6, 10.6); ax.set_aspect("equal"); ax.axis("off")
        # substrate
        ax.add_patch(Rectangle((0, 0), 10, 1.2, fc=col_sub, ec="none"))
        ax.text(5, 0.55, "substrate" + (" (GaN-on-Si)" if name == "GaN" else ""), ha="center", va="center", fontsize=6.5)
        ax.add_patch(Rectangle((0, 1.2), 10, 0.35, fc=col_ox, ec="none"))          # buried oxide
        # gate (common, wrapping both tiers): drawn as a tall block behind channels
        gx0, gx1 = 3.3, 6.7
        ax.add_patch(Rectangle((gx0, 1.55), gx1 - gx0, 7.6, fc=col_gate, ec="none", alpha=0.9))
        # S/D contacts left / right, bottom tier and top tier
        for (x0, x1) in ((0.9, 2.9), (7.1, 9.1)):
            ax.add_patch(Rectangle((x0, 1.55), x1 - x0, 2.9, fc=cn, ec="none", alpha=0.45))  # n S/D epi/contact
            ax.add_patch(Rectangle((x0, 5.55), x1 - x0, 2.9, fc=cp, ec="none", alpha=0.45))  # p S/D
            ax.add_patch(Rectangle((x0 + 0.5, 1.55), x1 - x0 - 1.0, 7.6, fc=col_ct, ec="none", alpha=0.0))
        # inter-tier dielectric
        ax.add_patch(Rectangle((0.9, 4.45), 8.2, 1.1, fc=col_ild, ec="#AAAAAA", lw=0.4))
        ax.text(1.0, 5.0, "inter-tier dielectric", ha="left", va="center", fontsize=5.5, color="#555555")
        # channels: bottom tier (n) and top tier (p)
        def draw_channels(kind, y0, y1, col, lab):
            ys = np.linspace(y0 + 0.45, y1 - 0.45, 3)
            if kind in ("ns", "ns_sige"):
                for y in ys:
                    ax.add_patch(Rectangle((2.3, y - 0.22), 5.4, 0.44, fc=col, ec="black", lw=0.3,
                                           hatch="////" if kind == "ns_sige" else None))
            elif kind == "2d":
                y = (y0 + y1) / 2
                ax.add_patch(Rectangle((2.3, y - 0.08), 5.4, 0.16, fc=col, ec="black", lw=0.3))
                ax.plot([2.3, 7.7], [y + 0.5, y + 0.5], color=col_ox, lw=1.5)   # top dielectric sketch
            elif kind == "cnt":
                y = (y0 + y1) / 2
                for xc in np.linspace(2.6, 7.4, 9):
                    ax.add_patch(plt.Circle((xc, y), 0.17, fc=col, ec="black", lw=0.3))
            elif kind == "2deg":
                ax.add_patch(Rectangle((2.3, y0 + 0.3), 5.4, 1.4, fc="#DDEBF7", ec="black", lw=0.3))   # GaN
                ax.add_patch(Rectangle((2.3, y0 + 1.7), 5.4, 0.5, fc="#9ECAE1", ec="black", lw=0.3))   # AlGaN barrier
                ax.plot([2.4, 7.6], [y0 + 1.7, y0 + 1.7], color=col, lw=2.0, ls=(0, (2, 1)))           # 2DEG
            elif kind == "pgan":
                ax.add_patch(Rectangle((2.3, y0 + 0.5), 5.4, 1.5, fc=col, ec="black", lw=0.3, alpha=0.8))
            ax.text(5.0, y1 + 0.02, lab, ha="center", va="bottom", fontsize=5.5, color=col, fontweight="bold")
        draw_channels(kb, 1.75, 4.25, cn, {"ns": "Si NS (n)", "2d": "MoS$_2$ 1L (n)", "cnt": "CNT array (n)", "2deg": "AlGaN/GaN 2DEG (n)"}[kb])
        draw_channels(kt, 5.75, 8.25, cp, {"ns": "Si NS (p)", "ns_sige": "SiGe NS (p)", "2d": "WSe$_2$ 1L (p)", "cnt": "CNT array (p)", "pgan": "p-GaN (p)"}[kt])
        # gate label and contacts text
        ax.text(5.0, 9.45, "common gate", ha="center", va="center", fontsize=6, color="black")
        ax.text(1.9, 3.0, "S/D\nn", ha="center", va="center", fontsize=5.5, color=cn)
        ax.text(8.1, 3.0, "S/D\nn", ha="center", va="center", fontsize=5.5, color=cn)
        ax.text(1.9, 7.0, "S/D\np", ha="center", va="center", fontsize=5.5, color=cp)
        ax.text(8.1, 7.0, "S/D\np", ha="center", va="center", fontsize=5.5, color=cp)
        ax.text(0.15, 2.9, "tier 1 (n)", rotation=90, ha="center", va="center", fontsize=5.5, color=cn)
        ax.text(0.15, 7.0, "tier 2 (p)", rotation=90, ha="center", va="center", fontsize=5.5, color=cp)
        # title and maturity tag
        ax.set_title(f"({'abcde'[i]}) {name}", fontsize=9, pad=3)
        tag_col = {"advanced-node": C["green"], "emerging post-Si": C["orange"], "exploratory / projected": C["purple"]}[tag]
        ax.add_patch(FancyBboxPatch((1.0, 9.75), 8.0, 0.65, boxstyle="round,pad=0.05", fc="white", ec=tag_col, lw=0.8))
        ax.text(5.0, 10.08, tag, ha="center", va="center", fontsize=6, color=tag_col)
        ax.text(5.0, -0.45, chan, ha="center", va="center", fontsize=5.5, wrap=True)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.02, wspace=0.08)
    out = os.path.join(FIG_DIR, "fig01_cfet_stacks.png")
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print(f"wrote {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    tb_device()
    inv_cfet()
    tb_inv()
    ro5_cfet()
    cfet_stacks()

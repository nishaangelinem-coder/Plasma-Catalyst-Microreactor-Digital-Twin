"""Publication schematics with schemdraw (vector PDF + 300-dpi PNG)."""
import os
import matplotlib
matplotlib.use('Agg')
import schemdraw
import schemdraw.elements as elm
from schemdraw import logic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, 'figures')
schemdraw.config(font='DejaVu Sans', fontsize=10, lw=1.3)


def save(d, name):
    d.save(os.path.join(FIG, name + '.pdf'))
    d.save(os.path.join(FIG, name + '.png'), dpi=300)


def branch(d, x0, y0, name, angle_label=None):
    """One series-mode branch: port -> (shunt Csh) -> mBVD -> Csw -> nMOS switch -> star. Drawn horizontally from (x0,y0)."""
    d += elm.Dot(open=True).at((x0, y0)).label(f'Port {name}\n50 Ω', 'left', ofst=0.15, fontsize=8)
    d += elm.Line().at((x0, y0)).right(0.8)
    P = d.here
    d += elm.Dot().at(P)
    d += elm.Capacitor().at(P).down().label('$C_{sh}$', 'right', fontsize=8, ofst=0.2)
    d += elm.Ground()
    d += elm.Resistor().at(P).right().label('$R_s$', 'top', fontsize=8)
    n1 = d.here
    d += elm.Dot().at(n1)
    # mBVD: upper branch R0 + C0, lower branch Rm + Lm + Cm
    d += elm.Line().at(n1).up(0.7)
    d += elm.Resistor().right().label('$R_0$', 'top', fontsize=8)
    d += elm.Capacitor().right().label('$C_0$', 'top', fontsize=8)
    d += elm.Line().right(1.5)
    top_end = d.here
    d += elm.Line().at(n1).down(0.7)
    d += elm.Resistor().right(1.0).label('$R_m$', 'bottom', fontsize=8)
    d += elm.Inductor2().right(1.0).label('$L_m$', 'bottom', fontsize=8)
    d += elm.Capacitor().right(1.0).label('$C_m$', 'bottom', fontsize=8)
    d += elm.Line().to((top_end[0], d.here[1]))
    bot_end = d.here
    d += elm.Line().at(top_end).to((top_end[0], bot_end[1]))
    M = (top_end[0], y0)
    d += elm.Dot().at(M).label(f'$M_{name}$', 'top', ofst=(-0.35, 0.1), fontsize=8)
    d += elm.Label().at((n1[0] + 1.6, y0 - 1.5)).label(f'mBVD res. {name}', fontsize=7)
    d += elm.Resistor().at(M).down(1.6).label('$R_b$', 'left', fontsize=7)
    d += elm.Ground()
    d += elm.Capacitor().at(M).right().label('$C_{sw}$', 'top', fontsize=8)
    Dn = d.here
    d += elm.Dot().at(Dn)
    # draw the switch as an nMOS with drain at Dn and source to the right
    d += elm.Line().at(Dn).right(0.4)
    fet = elm.NFet().right().anchor('drain').label(f'SW$_{name}$', 'bottom', fontsize=7)
    d += fet
    d += elm.Resistor().at(fet.gate).up(1.2).label('$R_g$', 'left', fontsize=7)
    d += elm.Dot(open=True).label(f'V$_{{G{name}}}$ (drv)', 'top', fontsize=7)
    d += elm.Line().at(fet.source).right(0.4)
    S = d.here
    return S


def fig_core():
    with schemdraw.Drawing(show=False) as d:
        d.config(unit=1.6, fontsize=9)
        ends = []
        for k, (y, name) in enumerate([(0.0, '1'), (-4.2, '2'), (-8.4, '3')]):
            ends.append(branch(d, 0.0, y, name))
        xs = max(e[0] for e in ends) + 1.0
        for e in ends:
            d += elm.Line().at(e).to((xs, e[1]))
            d += elm.Dot().at((xs, e[1]))
        d += elm.Line().at((xs, ends[0][1])).to((xs, ends[2][1]))
        d += elm.Label().at((xs + 0.2, ends[1][1] + 0.3)).label('star node\n(virtual ground for $l=\\pm1$,\nopen for $l=0$)', fontsize=7, halign='left')
        d += elm.Resistor().at((xs, ends[2][1])).down(1.4).label('$R_{star}$', 'right', fontsize=7)
        d += elm.Ground()
        save(d, 'fig_schematic_core')


def fig_phasegen():
    with schemdraw.Drawing(show=False) as d:
        d.config(unit=1.5, fontsize=9)
        ffs = []
        for i in range(3):
            f = elm.Ic(pins=[elm.IcPin(name='D', side='left', slot='2/2'),
                             elm.IcPin(name='CK', side='left', slot='1/2'),
                             elm.IcPin(name='Q', side='right', slot='2/2'),
                             elm.IcPin(name='QB', side='right', slot='1/2'),
                             elm.IcPin(name='RN', side='bottom', slot='1/1')],
                       size=(1.8, 2.0), leadlen=0.4, pinspacing=1.0).at((i * 4.4, 0)).anchor('center')
            d += f.label(f'FF{i}', 'top', ofst=0.1)
            ffs.append(f)
        # clock bus
        yb = -2.2
        d += elm.Dot(open=True).at((-2.6, yb)).label('CLK ($6f_m$)', 'left', fontsize=8)
        d += elm.Line().at((-2.6, yb)).to((ffs[2].CK[0] - 0.4, yb))
        for i, f in enumerate(ffs):
            p = f.CK
            d += elm.Line().at((p[0] - 0.4, yb)).to((p[0] - 0.4, p[1]))
            d += elm.Line().to(p)
            if i < 2:
                d += elm.Dot().at((p[0] - 0.4, yb))
        # reset bus
        yr = -2.9
        d += elm.Dot(open=True).at((-2.6, yr)).label('RSTN', 'left', fontsize=8)
        d += elm.Line().at((-2.6, yr)).to((ffs[2].RN[0], yr))
        for i, f in enumerate(ffs):
            p = f.RN
            d += elm.Line().at((p[0], yr)).to(p)
            if i < 2:
                d += elm.Dot().at((p[0], yr))
        # data chain
        for i in range(2):
            d += elm.Line().at(ffs[i].Q).to(ffs[i + 1].D)
        qb2, d0 = ffs[2].QB, ffs[0].D
        yt = 1.9
        d += elm.Line().at(qb2).right(0.5)
        d += elm.Line().to((qb2[0] + 0.5, yt))
        d += elm.Line().to((d0[0] - 0.6, yt))
        d += elm.Line().to((d0[0] - 0.6, d0[1]))
        d += elm.Line().to(d0)
        d += elm.Label().at((ffs[1].center[0], yt + 0.35)).label('$D_0 = \\overline{Q_2}$ (twisted ring)', fontsize=8)
        # outputs
        outs = [(ffs[0].Q, 'PH0 (0°)', 0.9), (ffs[2].Q, 'PH120 (120°)', 0.9), (ffs[1].QB, 'PH240 (240°)', 1.2)]
        for p, lab, dy in outs:
            d += elm.Dot().at(p)
            d += elm.Line().at(p).right(0.25)
            d += elm.Line().down(dy)
            d += elm.Arrow().right(0.8).label(lab, 'right', fontsize=8)
        d += elm.Label().at((ffs[1].center[0], -3.7)).label('state sequence 111→011→001→000→100→110 (÷6, 50 % duty)', fontsize=8)
        save(d, 'fig_schematic_phasegen')


def fig_driver(W=1000):
    with schemdraw.Drawing(show=False) as d:
        d.config(unit=1.4, fontsize=9)
        d += elm.Dot(open=True).label('PH$_n$', 'left')
        sizes = ['0.6/1.2', '1.8/3.6', '5.4/10.8', '16/32', '48/96']
        for s_ in sizes:
            d += elm.Line().right(0.4)
            d += logic.Not().right().label(s_, 'bottom', fontsize=7).label('$V_{DD}$', 'top', fontsize=7)
        d += elm.Line().right(0.5)
        g = d.here
        d += elm.Dot().at(g).label('$V_{Gn}(t)$', 'bottom', fontsize=8, ofst=0.3)
        d += elm.Resistor().at(g).right().label('$R_g$ 3 kΩ', 'top', fontsize=7)
        ge = d.here
        fet = elm.NFet(bulk=True).at(ge).anchor('gate').reverse().label(f'SW$_n$ (triple well)\nW = {W} µm, L = 65 nm', 'right', fontsize=7, ofst=1.2)
        d += fet
        d += elm.Line().at(fet.drain).up(0.5)
        d += elm.Capacitor().up().label('$C_{sw}$ (MIM)', 'left', fontsize=8)
        d += elm.Line().up(0.3)
        d += elm.Dot(open=True).label('$M_n$ (resonator)', 'top', fontsize=8)
        d += elm.Line().at(fet.source).down(0.9)
        src = d.here
        d += elm.Dot(open=True).at(src).label('star', 'bottom', fontsize=8)
        bx, by = fet.bulk[0] + 0.6, fet.bulk[1]
        d += elm.Line().at(fet.bulk).to((bx, by))
        d += elm.Resistor().at((bx, by)).down(1.2).label('$R_b$ 20 kΩ', 'right', fontsize=7)
        d += elm.Line().at((bx, by - 1.2)).to((bx, src[1] + 0.3))
        d += elm.Line().at((bx, src[1] + 0.3)).to((src[0], src[1] + 0.3))
        d += elm.Label().at((3.5, -2.6)).label('W$_n$/W$_p$ in µm, L = 65 nm; taper ×3; gate load ≈ 1.5 pF', fontsize=8)
        save(d, 'fig_schematic_driver')


def fig_dff():
    with schemdraw.Drawing(show=False) as d:
        d.config(unit=1.3, fontsize=8)
        d += elm.Dot(open=True).label('D', 'left')
        d += elm.Line().right(0.4)
        d += (tg1 := elm.Ic(pins=[elm.IcPin(side='left', pin=''), elm.IcPin(side='right', pin='')], size=(0.9, 0.7), leadlen=0.2).anchor('inL1').label('TG\n$\\overline{CK}$', fontsize=7))
        d += elm.Dot().at(tg1.inR1)
        m1 = tg1.inR1
        d += logic.Not().at(m1).right()
        m2 = d.here
        d += elm.Dot().at(m2)
        d += logic.Nand().at(m2).right().anchor('in1').label('RN', 'bottom', fontsize=7)
        m3 = d.here
        d += elm.Line().at(m3).right(0.3)
        d += elm.Line().down(1.6)
        d += (tg2 := elm.Ic(pins=[elm.IcPin(side='left', pin=''), elm.IcPin(side='right', pin='')], size=(0.9, 0.7), leadlen=0.2).anchor('inR1').label('TG\nCK', fontsize=7).left())
        d += elm.Line().at(tg2.inL1).to((m1[0], tg2.inL1[1]))
        d += elm.Line().to(m1)
        # slave
        d += elm.Line().at(m2).up(1.6)
        d += elm.Line().right(2.6)
        d += (tg3 := elm.Ic(pins=[elm.IcPin(side='left', pin=''), elm.IcPin(side='right', pin='')], size=(0.9, 0.7), leadlen=0.2).anchor('inL1').label('TG\nCK', fontsize=7))
        s1 = tg3.inR1
        d += elm.Dot().at(s1)
        d += logic.Not().at(s1).right()
        q = d.here
        d += elm.Dot().at(q).label('Q', 'top')
        d += elm.Line().at(q).right(0.8)
        d += logic.Not().right().label('$\\overline{Q}$', 'right')
        d += elm.Line().at(q).down(1.6)
        d += elm.Line().left(0.4)
        d += logic.Not().left()
        d += elm.Line().left(0.3)
        d += (tg4 := elm.Ic(pins=[elm.IcPin(side='left', pin=''), elm.IcPin(side='right', pin='')], size=(0.9, 0.7), leadlen=0.2).anchor('inR1').label('TG\n$\\overline{CK}$', fontsize=7).left())
        d += elm.Line().at(tg4.inL1).to((s1[0] - 0.9, tg4.inL1[1]))
        d += elm.Line().to((s1[0] - 0.9, s1[1]))
        d += elm.Line().to(s1)
        save(d, 'fig_schematic_dff')


if __name__ == '__main__':
    import json
    W = 1000
    try:
        W = int(round(json.load(open(os.path.join(ROOT, 'results', 'design_final.json')))['W_um']))
    except Exception:
        pass
    fig_core(); fig_phasegen(); fig_driver(W); fig_dff()
    print('schematics written')

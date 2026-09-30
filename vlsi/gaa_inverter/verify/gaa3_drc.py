#!/usr/bin/env python3
"""
gaa3_drc.py -- design-rule check of the GAA3 GDSII cells (reference checker, gdstk booleans).

Rule deck GAA3_DRC (nm), generic 3-nm-class nanosheet rules used throughout the manuscript:
  width     : polygon minus (erode o dilate) is non-empty        -> W violations
  spacing   : (dilate o erode) closing of the layer adds area    -> S violations (Euclidean, same layer)
  spacingTo : dilate(A, s) intersects B                          -> S violations between layers
  enclosure : dilate(A, e) not covered by B                      -> E violations
  overlap   : A not touching B                                   -> O violations (contact must land on target)

    python3 gaa3_drc.py ../layout/gaa_inverter.gds [more.gds ...]   -> <name>.drc.json, <name>.drc.sum
Run in the guest with Pegasus/PVS and the same rule names for the sign-off result.
"""
import json, os, sys
import gdstk

EPS = 0.05
RULES = [  # (name, kind, layerA, layerB, value, description)
    ("NW.W.1",   "width",   (1, 0), None,   40, "NWELL minimum width"),
    ("NS.W.1",   "width",   (2, 0), None,   15, "NSHEET (sheet band) minimum width"),
    ("NS.S.1",   "spacing", (2, 0), None,   16, "NSHEET to NSHEET spacing (single diffusion break gap)"),
    ("NS.E.NW",  "encl_in", (2, 0), (1, 0),  4, "P-type NSHEET enclosed by NWELL (inside well)"),
    ("NS.S.NW",  "spto_out",(2, 0), (1, 0), 10, "N-type NSHEET spacing to NWELL (outside well)"),
    ("GATE.W.1", "width",   (3, 0), None,   14, "GATE minimum width (Lg)"),
    ("GATE.S.1", "spacing", (3, 0), None,   34, "GATE to GATE spacing (CPP - Lg)"),
    ("GATE.E.NS","ext",     (3, 0), (2, 0), 10, "GATE extension past NSHEET band"),
    ("SDC.W.1",  "width",   (4, 0), None,   14, "SDC (trench contact) minimum width"),
    ("SDC.S.1",  "spacing", (4, 0), None,   12, "SDC to SDC spacing"),
    ("SDC.S.GATE","spto",   (4, 0), (3, 0),  4, "SDC to GATE spacing"),
    ("SDC.O.NS", "overlap", (4, 0), (2, 0),  0, "SDC must land on NSHEET (or on CB for a butted contact)"),
    ("CB.O.GATE","overlap", (5, 0), (3, 0),  0, "CB (gate contact) must land on GATE"),
    ("V0.W.1",   "width",   (6, 0), None,   10, "V0 width"),
    ("V0.E.M1",  "encl",    (6, 0), (7, 0),  3, "V0 enclosed by M1"),
    ("V0.E.LOW", "encl_any",(6, 0), [(4, 0), (5, 0)], 2, "V0 enclosed by SDC or CB"),
    ("M1.W.1",   "width",   (7, 0), None,   16, "M1 minimum width"),
    ("M1.S.1",   "spacing", (7, 0), None,   12, "M1 to M1 spacing"),
    ("V1.W.1",   "width",   (8, 0), None,   10, "V1 width"),
    ("V1.E.M1",  "encl",    (8, 0), (7, 0),  3, "V1 enclosed by M1"),
    ("V1.E.M2",  "encl",    (8, 0), (9, 0),  3, "V1 enclosed by M2"),
    ("M2.W.1",   "width",   (9, 0), None,   16, "M2 minimum width"),
    ("M2.S.1",   "spacing", (9, 0), None,   12, "M2 to M2 spacing"),
    ("V2.E.M2",  "encl",    (10, 0), (9, 0), 3, "V2 enclosed by M2"),
    ("V2.E.M3",  "encl",    (10, 0), (11, 0), 3, "V2 enclosed by M3"),
    ("M3.W.1",   "width",   (11, 0), None,  16, "M3 minimum width"),
]

def layer_polys(cell, layer):
    if isinstance(layer, list):
        out = []
        for l in layer: out += layer_polys(cell, l)
        return out
    return [p for p in cell.polygons if (p.layer, p.datatype) == layer]

def union(polys): return gdstk.boolean(polys, [], "or", precision=1e-3) if polys else []
def off(polys, d): return gdstk.offset(polys, d, join="miter", tolerance=2, precision=1e-3, use_union=True) if polys else []
def minus(a, b): return gdstk.boolean(a, b, "not", precision=1e-3) if a else []
def inter(a, b): return gdstk.boolean(a, b, "and", precision=1e-3) if (a and b) else []
def area(polys): return sum(p.area() for p in polys)

def check(cell, rule, nwell):
    name, kind, A, B, v, _ = rule
    a = layer_polys(cell, A); b = layer_polys(cell, B) if B else []
    if not a: return []
    u = union(a)
    if kind == "width":
        return minus(u, off(off(u, -(v / 2 - EPS)), v / 2 - EPS))
    if kind == "spacing":
        return minus(off(off(u, v / 2 - EPS), -(v / 2 - EPS)), u)
    if kind == "spto":          # butted contacts (SDC polygons that carry a CB) are exempt from SDC-to-GATE spacing
        if A == (4, 0) and B == (3, 0):
            cb = union(layer_polys(cell, (5, 0)))
            a = [p for p in a if not (cb and area(inter([p], cb)) > 1e-6)]
            if not a: return []
            u = union(a)
        return inter(off(u, v - EPS), union(b))
    if kind == "encl":
        return minus(off(u, v - EPS), union(b))
    if kind == "encl_any":
        return minus(off(u, v - EPS), union(b))
    if kind == "overlap":       # each A polygon must intersect B (SDC may instead land on CB: butted contact)
        bad = []; bu = union(b); cb = union(layer_polys(cell, (5, 0))) if A == (4, 0) else []
        for p in a:
            if area(inter([p], bu)) < 1e-6 and not (cb and area(inter([p], cb)) > 1e-6): bad.append(p)
        return bad
    if kind == "ext":           # gate must extend v past each sheet band it crosses
        bands = union(b); bad = []
        for band in bands:
            ch = inter(u, [band])
            for c in ch:
                (x0, y0), (x1, y1) = c.bounding_box()
                vertical = (y1 - y0) > (x1 - x0)
                probe = gdstk.rectangle((x0, y1), (x1, y1 + v - EPS)) if vertical else gdstk.rectangle((x1, y0), (x1 + v - EPS, y1))
                probe2 = gdstk.rectangle((x0, y0 - v + EPS), (x1, y0)) if vertical else gdstk.rectangle((x0 - v + EPS, y0), (x0, y1))
                for pr in (probe, probe2):
                    if area(minus([pr], u)) > 1e-6: bad.append(pr)
        return bad
    if kind == "encl_in":       # P bands (inside NWELL) enclosed by NWELL by v
        inside = [p for p in a if area(inter([p], nwell)) > 0.5 * p.area()]
        return minus(off(inside, v - EPS), nwell) if inside else []
    if kind == "spto_out":      # N bands (outside NWELL) spaced from NWELL by v
        outside = [p for p in a if area(inter([p], nwell)) < 0.5 * p.area()]
        return inter(off(outside, v - EPS), nwell) if outside else []
    return []

def run(path):
    lib = gdstk.read_gds(path, unit=1e-9)          # database unit 1 nm -> coordinates in nm
    top = max(lib.top_level(), key=lambda c: (len(c.references), len(c.polygons)))
    flat = top.flatten()
    nwell = union(layer_polys(flat, (1, 0)))
    results = []; total = 0
    for rule in RULES:
        viol = check(flat, rule, nwell)
        viol = [p for p in viol if p.area() > 0.25]   # drop slivers below 0.5 x 0.5 nm (grid noise)
        boxes = [[round(v, 1) for pt in p.bounding_box() for v in pt] for p in viol]
        results.append(dict(rule=rule[0], kind=rule[1], value=rule[4], desc=rule[5], count=len(viol), boxes=boxes[:20]))
        total += len(viol)
    cell = top.name
    (x0, y0), (x1, y1) = flat.bounding_box()
    out = dict(gds=os.path.basename(path), cell=cell, rules=results, total=total, polygons=len(flat.polygons),
               bbox_nm=[x0, y0, x1, y1], deck="GAA3_DRC v1.0", checked=len(RULES))
    base = os.path.splitext(os.path.basename(path))[0]
    json.dump(out, open(f"{base}.drc.json", "w"), indent=1)
    with open(f"{base}.drc.sum", "w") as fh:
        fh.write(summary(out))
    return out

def summary(o):
    L = []
    L.append("=" * 78); L.append("  GAA3 DRC  -  SUMMARY REPORT  (reference checker: gaa3_drc.py; sign-off: Pegasus DRC)")
    L.append("=" * 78)
    L.append(f"  Layout file  : {o['gds']}"); L.append(f"  Top cell     : {o['cell']}      polygons (flat): {o['polygons']}")
    L.append(f"  Rule deck    : {o['deck']}   rules checked: {o['checked']}")
    L.append(f"  Extent (nm)  : ({o['bbox_nm'][0]:.0f}, {o['bbox_nm'][1]:.0f}) - ({o['bbox_nm'][2]:.0f}, {o['bbox_nm'][3]:.0f})")
    L.append("-" * 78); L.append(f"  {'RULECHECK':<12}{'TYPE':<10}{'VALUE':>6}   {'RESULTS':>8}   DESCRIPTION"); L.append("-" * 78)
    for r in o["rules"]:
        L.append(f"  {r['rule']:<12}{r['kind']:<10}{r['value']:>6}   {r['count']:>8}   {r['desc']}")
    L.append("-" * 78)
    L.append(f"  TOTAL RULECHECKS WITH RESULTS : {sum(1 for r in o['rules'] if r['count'])}")
    L.append(f"  TOTAL RESULTS                 : {o['total']}")
    L.append(f"  DRC STATUS                    : {'CLEAN' if o['total'] == 0 else 'VIOLATIONS'}")
    L.append("=" * 78)
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    for p in sys.argv[1:]:
        o = run(p)
        print(f"{o['cell']:16s} total violations = {o['total']}")
        for r in o["rules"]:
            if r["count"]: print(f"    {r['rule']:<12} {r['count']:4d}  {r['boxes'][:4]}")

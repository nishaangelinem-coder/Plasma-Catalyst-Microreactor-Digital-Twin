#!/usr/bin/env python3
"""
gaa3_lvs.py -- layout-versus-schematic of the GAA3 cells (reference extractor + comparator).

Extraction (flattened GDSII, gdstk):
  * conductors : GATE, SDC, CB, M1, M2, M3 and the diffusion segments NSHEET - GATE
  * connections: same-layer touch; SDC-diffusion; CB-GATE; SDC-CB (butted); V0: M1-SDC/CB;
                 V1: M1-M2; V2: M2-M3
  * devices    : every GATE x NSHEET intersection is a nanosheet transistor; type from NWELL,
                 W = channel extent along the gate, L = across it; S/D = the two adjacent
                 diffusion segments; texts on M1/M2/M3 name the nets (ports)
Comparison: colour refinement over the device/net graph (type, width and terminal roles), then the
multisets of device and net classes are compared -> MATCH / MISMATCH with counts, PVS-style report.

    python3 gaa3_lvs.py <cell.gds> <schematic.scs> <subckt>     -> <cell>.lvs.json / .lvs.rpt
"""
import json, os, re, sys
import gdstk

CONDUCTORS = {(3, 0): "GATE", (4, 0): "SDC", (5, 0): "CB", (7, 0): "M1", (9, 0): "M2", (11, 0): "M3"}
VIAS = {(6, 0): [(7, 0), (4, 0), (5, 0)], (8, 0): [(7, 0), (9, 0)], (10, 0): [(9, 0), (11, 0)]}
TEXT_LAYERS = {(7, 2): (7, 0), (9, 2): (9, 0), (11, 2): (11, 0)}          # pin texts (ports)
NET_TEXT_LAYERS = {(7, 3): (7, 0), (9, 3): (9, 0), (11, 3): (11, 0)}      # net-name texts (streamOut -outputNetNames)
GLOBALS = {"VDD", "VSS", "vdd!", "gnd!"}

def touches(a, b):
    (ax0, ay0), (ax1, ay1) = a.bounding_box(); (bx0, by0), (bx1, by1) = b.bounding_box()
    if ax1 < bx0 - 1e-6 or bx1 < ax0 - 1e-6 or ay1 < by0 - 1e-6 or by1 < ay0 - 1e-6: return False
    return sum(p.area() for p in gdstk.boolean([a], [b], "and", precision=1e-3)) > 1e-6 or \
        sum(p.area() for p in gdstk.boolean(gdstk.offset([a], 0.01, precision=1e-3), [b], "and", precision=1e-3)) > 1e-6

class UF:
    def __init__(self): self.p = {}
    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x: self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b): self.p[self.find(a)] = self.find(b)

def extract(path):
    lib = gdstk.read_gds(path, unit=1e-9); top = max(lib.top_level(), key=lambda c: (len(c.references), len(c.polygons)))
    top_labels = list(top.labels)                                        # before flatten(): flatten() works in place
    flat = top.flatten()
    polys = {}
    for p in flat.polygons: polys.setdefault((p.layer, p.datatype), []).append(p)
    nwell = gdstk.boolean(polys.get((1, 0), []), [], "or", precision=1e-3)
    gate = gdstk.boolean(polys.get((3, 0), []), [], "or", precision=1e-3)
    sheet = gdstk.boolean(polys.get((2, 0), []), [], "or", precision=1e-3)
    diff = gdstk.boolean(sheet, gate, "not", precision=1e-3)            # diffusion segments
    chan = gdstk.boolean(sheet, gate, "and", precision=1e-3)            # channels
    shapes = []                                                         # (id, layer, polygon)
    for lay, ps in polys.items():
        if lay in CONDUCTORS:
            for p in gdstk.boolean(ps, [], "or", precision=1e-3): shapes.append((len(shapes), lay, p))
    for p in diff: shapes.append((len(shapes), "DIFF", p))
    uf = UF()
    def sid(i): return f"s{i}"
    by_layer = {}
    for i, lay, p in shapes: by_layer.setdefault(lay, []).append((i, p))
    def connect(la, lb):
        for i, p in by_layer.get(la, []):
            for j, q in by_layer.get(lb, []):
                if i != j and touches(p, q): uf.union(sid(i), sid(j))
    connect((4, 0), "DIFF"); connect((5, 0), (3, 0)); connect((4, 0), (5, 0))
    for vlay, targets in VIAS.items():
        for v in polys.get(vlay, []):
            hit = [i for t in targets for i, p in by_layer.get(t, []) if touches(v, p)]
            for i in hit[1:]: uf.union(sid(hit[0]), sid(i))
    # texts -> net names (labels inside referenced cells are hierarchical unless global supplies)
    names = {}; ports = set()
    labels = top_labels + [lab for lab in flat.labels if lab.text in GLOBALS and lab not in top_labels]   # hierarchical labels: only globals
    for is_port, layers in ((True, TEXT_LAYERS), (False, NET_TEXT_LAYERS)):
        for lab in labels:
            lay = (lab.layer, lab.texttype)
            if lay not in layers: continue
            pt = gdstk.rectangle((lab.origin[0] - 0.5, lab.origin[1] - 0.5), (lab.origin[0] + 0.5, lab.origin[1] + 0.5))
            for i, p in by_layer.get(layers[lay], []):
                if touches(pt, p):
                    net = uf.find(sid(i)); txt = lab.text
                    if txt in GLOBALS or txt not in names.values() or names.get(net) == txt:
                        names.setdefault(net, txt)
                        if is_port and names[net] == txt: ports.add(txt)
    # virtual connect by name for global supplies (separate rail pieces of the same net)
    byname = {}
    for net, txt in list(names.items()):
        if txt in GLOBALS:
            if txt in byname: uf.union(net, byname[txt])
            else: byname[txt] = net
    names = {uf.find(n): t for n, t in names.items()}
    ports = {t for t in ports}
    # devices
    devices = []
    for k, ch in enumerate(chan):
        (x0, y0), (x1, y1) = ch.bounding_box()
        vertical = (y1 - y0) > (x1 - x0)                                # gate runs vertically -> current flows in x
        W, Lg = ((y1 - y0), (x1 - x0)) if vertical else ((x1 - x0), (y1 - y0))
        ptype = sum(p.area() for p in gdstk.boolean([ch], nwell, "and", precision=1e-3)) > 0.5 * ch.area()
        g = [i for i, p in by_layer.get((3, 0), []) if touches(ch, p)]
        sd = [i for i, p in by_layer.get("DIFF", []) if touches(gdstk.offset([ch], 0.6, precision=1e-3)[0], p)]
        if len(sd) != 2 or not g:
            devices.append(dict(type="?", W=W, L=Lg, g=None, sd=[], bad=True)); continue
        devices.append(dict(type="p" if ptype else "n", W=round(W), L=round(Lg), g=uf.find(sid(g[0])),
                            sd=sorted(uf.find(sid(i)) for i in sd)))
    nets = {}
    for d in devices:
        for n in ([d["g"]] if d["g"] else []) + d["sd"]:
            nets.setdefault(n, names.get(n))
    # original (un-merged) polygons tagged with their net, for parasitic extraction
    geom = []
    for lay, ps in polys.items():
        if lay in CONDUCTORS or lay in VIAS:
            for p in ps:
                targets = [lay] if lay in CONDUCTORS else VIAS[lay]
                net = None
                for t in targets:
                    for i, q in by_layer.get(t, []):
                        if touches(p, q): net = uf.find(sid(i)); break
                    if net: break
                geom.append(dict(layer=lay, bbox=[round(v, 2) for pt in p.bounding_box() for v in pt], net=net))
    for i, p in by_layer.get("DIFF", []):
        geom.append(dict(layer="DIFF", bbox=[round(v, 2) for pt in p.bounding_box() for v in pt], net=uf.find(sid(i))))
    return dict(cell=top.name, devices=devices, nets=nets, names=names, ports=ports, geom=geom, channels=[list(c.bounding_box()) for c in chan])

def parse_spectre(path, sub):
    """Minimal Spectre subset: model cards (type, hfin), subckt/ends, M devices, X instances, include."""
    models, subs = {}, {}
    def load(p, seen=set()):
        p = os.path.abspath(p)
        if p in seen: return
        seen.add(p)
        cur = None
        text = open(p).read().replace("\\\n", " ")          # join Spectre line continuations
        for raw in text.splitlines():
            line = raw.split("//")[0].strip()
            if not line: continue
            t = line.split()
            if t[0] == "include":
                load(os.path.join(os.path.dirname(p), t[1].strip('"')))
            elif t[0] == "model" and "bsimcmg" in line:
                hf = re.search(r"hfin=([0-9.]+)e-9", line); ty = re.search(r"type=([np])", line)
                models[t[1]] = dict(type=ty.group(1), W=round(float(hf.group(1))))      # sheet width hfin (nm) = layout band width
            elif t[0] == "subckt":
                cur = t[1]; subs[cur] = dict(ports=re.search(r"\((.*?)\)", line).group(1).split(), lines=[])
            elif t[0] == "ends":
                cur = None
            elif cur:
                subs[cur]["lines"].append(line)
    load(path)
    devices = []; net_alias = UF()
    def expand(name, portmap, prefix):
        for line in subs[name]["lines"]:
          for m in re.finditer(r"(\w+)\s*\((.*?)\)\s*(\w+)", line):        # several statements may share a line
              inst, nodes, ref = m.group(1), m.group(2).split(), m.group(3)
              nodes = [portmap.get(n, prefix + n if n not in GLOBALS else n) for n in nodes]
              if ref in models:
                  d, g, s, b = nodes[:4]
                  devices.append(dict(type=models[ref]["type"], W=models[ref]["W"], g=g, sd=sorted([d, s]), inst=prefix + inst))
              elif ref in subs:
                  expand(ref, dict(zip(subs[ref]["ports"], nodes)), prefix + inst + "/")
              elif ref == "resistor" and "r=0" in line:
                  net_alias.union(nodes[0], nodes[1])
    expand(sub, {p: p for p in subs[sub]["ports"]}, "")
    for d in devices:
        d["g"] = net_alias.find(d["g"]); d["sd"] = sorted(net_alias.find(n) for n in d["sd"])
    ports = set(net_alias.find(p) for p in subs[sub]["ports"])
    return dict(cell=sub, devices=devices, ports=ports)

def refine(devices, netname, rounds=8):
    """Colour refinement: nets start from their port names (or 'int'), devices from (type, W)."""
    nets = {n for d in devices for n in [d["g"]] + d["sd"]}
    ncol = {n: ("port:" + netname(n)) if netname(n) else "int" for n in nets}
    for _ in range(rounds):
        dcol = {id(d): (d["type"], d["W"], ncol[d["g"]], tuple(sorted(ncol[n] for n in d["sd"]))) for d in devices}
        new = {}
        for n in nets:
            inc = []
            for d in devices:
                if d["g"] == n: inc.append(("g", dcol[id(d)]))
                for m in d["sd"]:
                    if m == n: inc.append(("sd", dcol[id(d)]))
            new[n] = (ncol[n], tuple(sorted(map(str, inc))))
        # compress
        keys = {v: i for i, v in enumerate(sorted(set(map(str, new.values()))))}
        ncol2 = {n: (ncol[n].split("|")[0] + "|" + str(keys[str(new[n])])) for n in nets}
        if all(ncol2[n].split("|")[0] == ncol[n].split("|")[0] for n in nets) and len(set(ncol2.values())) == len(set(ncol.values())):
            ncol = ncol2; break
        ncol = ncol2
    dcol = sorted(str((d["type"], d["W"], ncol[d["g"]], tuple(sorted(ncol[n] for n in d["sd"])))) for d in devices)
    return dcol, sorted(ncol.values()), ncol

def compare(lay, sch):
    ldev = [d for d in lay["devices"] if not d.get("bad")]
    lname = lambda n: lay["nets"].get(n) if lay["nets"].get(n) in lay["ports"] else None
    sname = lambda n: n if n in sch["ports"] else None
    ld, ln, lcol = refine(ldev, lname); sd, sn, scol = refine(sch["devices"], sname)
    lay_ports = sorted({v for v in lay["nets"].values() if v and v in lay["ports"]}); sch_ports = sorted(sch["ports"])
    res = dict(layout_cell=lay["cell"], schematic_cell=sch["cell"],
               layout=dict(ports=len(lay_ports), nets=len(lay["nets"]), instances=len(ldev),
                           n=sum(d["type"] == "n" for d in ldev), p=sum(d["type"] == "p" for d in ldev), port_names=lay_ports,
                           unrecognised=sum(1 for d in lay["devices"] if d.get("bad"))),
               schematic=dict(ports=len(sch_ports), nets=len({n for d in sch["devices"] for n in [d["g"]] + d["sd"]}),
                              instances=len(sch["devices"]), n=sum(d["type"] == "n" for d in sch["devices"]),
                              p=sum(d["type"] == "p" for d in sch["devices"]), port_names=sch_ports),
               device_classes_match=(ld == sd), net_classes_match=(ln == sn), port_names_match=(lay_ports == sch_ports))
    res["result"] = "MATCH" if res["device_classes_match"] and res["net_classes_match"] and res["port_names_match"] and not res["layout"]["unrecognised"] else "MISMATCH"
    if res["result"] == "MISMATCH":
        from collections import Counter
        cl, cs = Counter(ld), Counter(sd)
        res["layout_only_devices"] = sorted((cl - cs).elements()); res["schematic_only_devices"] = sorted((cs - cl).elements())
    return res

def report(r):
    L = ["=" * 78, "  GAA3 LVS  -  CELL COMPARISON RESULTS  (reference extractor: gaa3_lvs.py; sign-off: Pegasus LVS)", "=" * 78,
         f"  LAYOUT CELL    : {r['layout_cell']}", f"  SCHEMATIC CELL : {r['schematic_cell']}", "-" * 78,
         f"  {'OBJECT':<14}{'LAYOUT':>10}{'SCHEMATIC':>12}   STATUS", "-" * 78]
    for key, lab in (("ports", "Ports"), ("nets", "Nets"), ("instances", "Instances"), ("n", "  NMOS (nsheet_n)"), ("p", "  PMOS (nsheet_p)")):
        a, b = r["layout"][key], r["schematic"][key]
        L.append(f"  {lab:<14}{a:>10}{b:>12}   {'ok' if a == b else 'DIFFERENT'}")
    L += ["-" * 78, f"  Port names     : layout {r['layout']['port_names']}", f"                   schematic {r['schematic']['port_names']}",
          f"  Device classes : {'match' if r['device_classes_match'] else 'MISMATCH'}   Net classes : {'match' if r['net_classes_match'] else 'MISMATCH'}",
          "-" * 78, f"  RESULT         : {r['result']}", "=" * 78]
    if r["result"] == "MISMATCH":
        L += ["  layout-only devices    : " + "; ".join(r["layout_only_devices"]), "  schematic-only devices : " + "; ".join(r["schematic_only_devices"])]
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    gds, scs, sub = sys.argv[1:4]
    lay = extract(gds); sch = parse_spectre(scs, sub)
    r = compare(lay, sch)
    base = os.path.splitext(os.path.basename(gds))[0]
    json.dump(r, open(f"{base}.lvs.json", "w"), indent=1); open(f"{base}.lvs.rpt", "w").write(report(r))
    print(report(r))

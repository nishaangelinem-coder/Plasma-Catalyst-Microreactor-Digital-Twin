#!/usr/bin/env python3
"""
innovus_ref.py -- reference place-and-route for the GAA3 flow (the Innovus step of Fig. 5, run here without the tool).

  init_design : mapped netlist (out/<design>.json from genus_ref.py), cell abstracts (pin rectangles of gaa3_stdcells.lef)
  floorPlan   : one gaa3_core row (168 nm), core width = cell width / target utilisation rounded to the 48-nm site
  place       : cells in netlist (chain) order, spread evenly on sites; FILL_GAA_X1 in the gaps
  pin assign  : input pins on the left die edge, outputs on the right, on M2
  route       : every signal net on one horizontal M2 track (28-nm pitch) chosen greedily so that horizontal
                segments and the vertical jogs from the pins do not conflict; V1 on the M1 pins
  outputs     : out/<design>.def, out/<design>.gds (SREFs of the cell GDSII + M2/V1 routing, pin texts),
                out/<design>_pnr.json (placement, routes, wirelength, vias), out/<design>_pnr.scs (LVS source)
  post-route  : gaa3_drc on the GDS, gaa3_lvs against the mapped netlist, gaa3_pex -> SPEF, timing with the
                extracted net capacitances (report_timing -postRoute), verify summary

    python3 innovus_ref.py inverter nand2 ring_osc
"""
import json, os, subprocess, sys
R = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(R)
sys.path.insert(0, os.path.join(B, "layout")); sys.path.insert(0, os.path.join(B, "verify")); sys.path.insert(0, R)
import gen_gaa_inverter_gds as ginv, gen_gaa_nand2_gds as gnand
import genus_ref as syn

SITE, ROW_H, UTIL = 48, 168, 0.60
TRACKS = [84, 56, 112, 140, 28]                 # M2 tracks in order of preference (pin level first: no jog)
M2W, V1 = 16, 10
L_V1, L_M2, L_M2PIN, L_M2TXT = (8, 0), (9, 0), (9, 1), (9, 2)
CELLS = {  # width, pins: name -> (layer, x0, y0, x1, y1) in cell coordinates; obs: cell-internal M2 (LEF OBS), tagged with the pin it carries
    "INV_GAA_X1": dict(w=96, pins=dict(A=("M1", 39, 76, 55, 92), Y=("M1", 67, 34, 83, 134)), obs=[]),
    "NAND2_GAA_X1": dict(w=144, pins=dict(A=("M1", 40, 76, 56, 92), B=("M1", 84, 76, 100, 92), Y=("M2", 112, 76, 128, 92)),
                         obs=[(64, 111, 128, 127, "Y"), (112, 76, 128, 127, "Y")]),
    "FILL_GAA_X1": dict(w=48, pins={}, obs=[]),
}
SP = 12                                          # M2 spacing

def gap(a, b):
    """spacing between two rects (x0,y0,x1,y1): negative when they overlap"""
    dx = max(b[0] - a[2], a[0] - b[2]); dy = max(b[1] - a[3], a[1] - b[3])
    return max(dx, dy) if (dx > 0 or dy > 0) else max(dx, dy)

def conflicts(rects, others):
    for r in rects:
        for o in others:
            if gap(r, o) < SP: return True
    return False

def build_fill():
    c = ginv.GdsCell("FILL_GAA_X1"); L = ginv.L; lg2 = ginv.TECH["LG"] // 2; rw = ginv.TECH["RAIL_W"] // 2
    c.rect(*L["PRBOUND"], 0, 0, SITE, ROW_H, "prBoundary"); c.rect(*L["NWELL"], 0, ROW_H // 2, SITE, ROW_H, "NWELL")
    c.rect(*L["GATE"], -lg2, 14, lg2, ROW_H - 14, "dummy"); c.rect(*L["GATE"], SITE - lg2, 14, SITE + lg2, ROW_H - 14, "dummy")
    c.rect(*L["M1"], -4, -rw, SITE + 4, rw, "VSS rail"); c.rect(*L["M1"], -4, ROW_H - rw, SITE + 4, ROW_H + rw, "VDD rail")
    return c

def place(net, obstructed_last=True, flip_obstructed=False):
    order = []
    # chain order: follow the nets from the inputs (keeps connected cells adjacent)
    drivers = {i["pins"]["Y"]: i for i in net["insts"]}; seen = set()
    frontier = list(net["ports"]["inputs"])
    while frontier:
        n = frontier.pop(0)
        for i in net["insts"]:
            if i["name"] in seen: continue
            if n in [v for p, v in i["pins"].items() if p != "Y"]:
                seen.add(i["name"]); order.append(i); frontier.append(i["pins"]["Y"])
    for i in net["insts"]:
        if i["name"] not in seen: order.append(i)
    if obstructed_last:
        order = [i for i in order if not CELLS[i["cell"]]["obs"]] + [i for i in order if CELLS[i["cell"]]["obs"]]
    total = sum(CELLS[i["cell"]]["w"] for i in order)
    core_w = int(-(-total / UTIL // SITE)) * SITE
    slack = core_w - total; gaps = len(order) + 1
    gap_sites = [slack // SITE // gaps] * gaps
    for k in range((slack // SITE) % gaps): gap_sites[k] += 1
    x = 0; placed = []; fills = []
    for k, inst in enumerate(order):
        for _ in range(gap_sites[k]): fills.append(x); x += SITE
        placed.append(dict(name=inst["name"], cell=inst["cell"], x=x, pins=inst["pins"], flip=bool(flip_obstructed and CELLS[inst["cell"]]["obs"]))); x += CELLS[inst["cell"]]["w"]
    for _ in range(gap_sites[-1]): fills.append(x); x += SITE
    return placed, fills, core_w

def route(net, placed, core_w):
    pins_of = {}                                                 # net -> list of (x, ylo, yhi, layer, tag)
    def cx(p, x0, x1):                                    # cell x-range -> placed x-range (mirrored if the cell is flipped)
        w = CELLS[p["cell"]]["w"]
        return (p["x"] + w - x1, p["x"] + w - x0) if p.get("flip") else (p["x"] + x0, p["x"] + x1)
    for p in placed:
        for pin, n in p["pins"].items():
            lay, x0, y0, x1, y1 = CELLS[p["cell"]]["pins"][pin]
            a, b = cx(p, x0, x1)
            pins_of.setdefault(n, []).append(dict(x=(a + b) // 2, ylo=y0, yhi=y1, layer=lay, tag=f"{p['name']}/{pin}"))
    io = {}
    ins, outs = net["ports"]["inputs"], net["ports"]["outputs"]
    for k, n in enumerate(ins):
        y = TRACKS[k % len(TRACKS)]
        io[n] = dict(x=8, ylo=y, yhi=y, layer="M2", tag=f"PIN {n}", side="W"); pins_of.setdefault(n, []).append(io[n])
    for k, n in enumerate(outs):
        y = TRACKS[k % len(TRACKS)]
        io[n] = dict(x=core_w - 8, ylo=y, yhi=y, layer="M2", tag=f"PIN {n}", side="E"); pins_of.setdefault(n, []).append(io[n])
    obs = []                                                     # (rect, net-or-None): cell M2 obstructions, tagged by the net on that pin
    for p in placed:
        for x0, y0, x1, y1, pin in CELLS[p["cell"]]["obs"]:
            a, b = cx(p, x0, x1); obs.append(((a, y0, b, y1), p["pins"].get(pin)))
    metal = []                                                   # (rect, net) of everything routed so far, plus I/O pin metal
    for n, p in io.items(): metal.append(((p["x"] - 8, p["ylo"] - 8, p["x"] + 8, p["ylo"] + 8), n))
    routes = {}
    for n in sorted(pins_of, key=lambda n: min(p["x"] for p in pins_of[n])):
        ps = pins_of[n]
        if len(ps) < 2: continue
        xmin, xmax = min(p["x"] for p in ps), max(p["x"] for p in ps)
        for t in TRACKS:
            def landing(p):
                if p["layer"] == "M2" or p["ylo"] == p["yhi"]:
                    return t if p["ylo"] <= t <= p["yhi"] else (p["ylo"] + p["yhi"]) // 2
                return t if p["ylo"] + 8 <= t <= p["yhi"] - 8 else (p["ylo"] + p["yhi"]) // 2
            need = [(p["x"], min(t, landing(p)), max(t, landing(p))) for p in ps if landing(p) != t]
            rects = [(xmin - M2W // 2, t - M2W // 2, xmax + M2W // 2, t + M2W // 2)] + [(jx - M2W // 2, jlo - M2W // 2, jx + M2W // 2, jhi + M2W // 2) for jx, jlo, jhi in need]
            others = [r for r, m in metal if m != n] + [r for r, m in obs if m != n]
            if not conflicts(rects, others):
                metal += [(r, n) for r in rects]
                routes[n] = dict(track=t, x0=xmin, x1=xmax, jogs=need, pins=ps); break
        else:
            raise RuntimeError(f"no free track for net {n}")
    return routes, io

def emit(net, placed, fills, core_w, routes, io, d):
    lib = ginv.GdsLibrary("GAA3_INV_LIB")
    cinv = ginv.build_inverter(); cnand = gnand.build_nand2(); cfill = build_fill()
    top = ginv.GdsCell(net["design"]); flat = ginv.GdsCell(net["design"] + "_flat")
    cellmap = {"INV_GAA_X1": cinv, "NAND2_GAA_X1": cnand, "FILL_GAA_X1": cfill}
    for p in placed:
        w = CELLS[p["cell"]]["w"]
        if p.get("flip"): top.ref(p["cell"], p["x"] + w, 0, mirror_x=True)
        else: top.ref(p["cell"], p["x"], 0)
        tf = (lambda x: p["x"] + w - x) if p.get("flip") else (lambda x: x + p["x"])
        for layer, dt, pts, tag in cellmap[p["cell"]].polygons: flat.polygons.append((layer, dt, [(tf(x), y) for x, y in pts], f"{p['name']} {tag}"))
    for x in fills:
        top.ref("FILL_GAA_X1", x, 0)
        for layer, dt, pts, tag in cfill.polygons: flat.polygons.append((layer, dt, [(xx + x, y) for xx, y in pts], "fill " + tag))
    wl = 0; nv = 0
    def draw(c):
        nonlocal wl, nv
        for n, r in routes.items():
            t = r["track"]
            c.rect(*L_M2, r["x0"] - M2W // 2, t - M2W // 2, r["x1"] + M2W // 2, t + M2W // 2, f"net {n}")
            c.label(9, 3, (r["x0"] + r["x1"]) // 2, t, n)                        # net name text (streamOut -outputNetNames)
            for jx, jlo, jhi in r["jogs"]: c.rect(*L_M2, jx - M2W // 2, jlo - M2W // 2, jx + M2W // 2, jhi + M2W // 2, f"net {n} jog")
            for p in r["pins"]:
                if p["layer"] == "M1":
                    y = t if p["ylo"] + 8 <= t <= p["yhi"] - 8 else (p["ylo"] + p["yhi"]) // 2
                    c.rect(*L_V1, p["x"] - V1 // 2, y - V1 // 2, p["x"] + V1 // 2, y + V1 // 2, f"V1 {p['tag']}")
                    if y != t: c.rect(*L_M2, p["x"] - M2W // 2, y - M2W // 2, p["x"] + M2W // 2, y + M2W // 2, f"net {n} landing")
        for n, p in io.items():
            c.rect(*L_M2, p["x"] - 8, p["ylo"] - 8, p["x"] + 8, p["ylo"] + 8, f"pin {n} metal")
            c.rect(*L_M2PIN, p["x"] - 8, p["ylo"] - 8, p["x"] + 8, p["ylo"] + 8, f"pin {n}"); c.label(*L_M2TXT, p["x"], p["ylo"], n)
        c.rect(*ginv.L["PRBOUND"], 0, 0, core_w, ROW_H, "core")
    draw(top); draw(flat)
    for n, r in routes.items():
        wl += (r["x1"] - r["x0"]) + sum(jhi - jlo for _, jlo, jhi in r["jogs"]); nv += sum(1 for p in r["pins"] if p["layer"] == "M1")
    used = {p["cell"] for p in placed} | ({"FILL_GAA_X1"} if fills else set())
    lib.cells += [c for c in (cinv, cnand, cfill) if c.name in used] + [top]
    lib.write(os.path.join(R, "out", f"{d}.gds"))
    ginv.STYLE.update({L_V1: ("#ffeb3b", "#8d6e00", 1.0), L_M2: ("#8e24aa", "#4a148c", 0.55), L_M2PIN: ("none", "#4a148c", 1.0)})
    open(os.path.join(R, "out", f"{d}.svg"), "w").write(ginv.to_svg(flat, pad=16, scale=1.6 if core_w > 600 else 3.0))
    # DEF
    D = [f"VERSION 5.8 ;", f"DESIGN {net['design']} ;", "UNITS DISTANCE MICRONS 1000 ;", f"DIEAREA ( 0 0 ) ( {core_w} {ROW_H} ) ;",
         f"ROW row_0 gaa3_core 0 0 N DO {core_w // SITE} BY 1 STEP {SITE} 0 ;", f"COMPONENTS {len(placed) + len(fills)} ;"]
    for p in placed: D.append(f"  - {p['name']} {p['cell']} + PLACED ( {p['x']} 0 ) {'FN' if p.get('flip') else 'N'} ;")
    for k, x in enumerate(fills): D.append(f"  - FILL{k} FILL_GAA_X1 + PLACED ( {x} 0 ) N ;")
    D += ["END COMPONENTS", f"PINS {len(io)} ;"]
    for n, p in io.items(): D.append(f"  - {n} + NET {n} + DIRECTION {'INPUT' if p['side'] == 'W' else 'OUTPUT'} + LAYER M2 ( -8 -8 ) ( 8 8 ) + PLACED ( {p['x']} {p['ylo']} ) N ;")
    D += ["END PINS", f"NETS {len(routes)} ;"]
    for n, r in routes.items():
        conns = " ".join(f"( {p['tag'].split('/')[0] if 'PIN' not in p['tag'] else 'PIN'} {p['tag'].split('/')[-1].replace('PIN ', '')} )" for p in r["pins"])
        seg = f"+ ROUTED M2 ( {r['x0']} {r['track']} ) ( {r['x1']} {r['track']} )"
        for jx, jlo, jhi in r["jogs"]: seg += f" NEW M2 ( {jx} {jlo} ) ( {jx} {jhi} )"
        D.append(f"  - {n} {conns} {seg} ;")
    D += ["END NETS", "END DESIGN"]
    open(os.path.join(R, "out", f"{d}.def"), "w").write("\n".join(D) + "\n")
    # LVS source: the mapped netlist as a Spectre subcircuit of library cells
    S = ["simulator lang=spectre", 'include "../../spectre/gaa_inv_tb.scs" section=models', 'include "../../spectre/gaa_nand2_tb.scs" section=models',
         f"subckt {net['design']} ({' '.join(net['ports']['inputs'] + net['ports']['outputs'])} VDD VSS)"]
    for k, i in enumerate(net["insts"]):
        pins = i["pins"]; nets_ = [pins[p].replace("[", "_").replace("]", "") for p in (("A", "Y") if i["cell"] == "INV_GAA_X1" else ("A", "B", "Y"))]
        S.append(f"    X{k} ({' '.join(nets_)} VDD VSS) {i['cell']}")
    S.append(f"ends {net['design']}")
    open(os.path.join(R, "out", f"{d}_pnr.scs"), "w").write("\n".join(S) + "\n")
    return dict(core_w=core_w, cells=len(placed), fills=len(fills), utilisation=sum(CELLS[p["cell"]]["w"] for p in placed) / core_w,
                nets=len(routes), wirelength_nm=wl, vias=nv, tracks_used=sorted({r["track"] for r in routes.values()}),
                placed=[dict(name=p["name"], cell=p["cell"], x=p["x"], w=CELLS[p["cell"]]["w"], flip=p.get("flip", False)) for p in placed], fill_x=fills,
                routes={n: dict(track=r["track"], x0=r["x0"], x1=r["x1"], jogs=r["jogs"], vias=[(p["x"], (r["track"] if p["ylo"] + 8 <= r["track"] <= p["yhi"] - 8 else (p["ylo"] + p["yhi"]) // 2)) for p in r["pins"] if p["layer"] == "M1"]) for n, r in routes.items()},
                pins={n: dict(x=p["x"], y=p["ylo"], side=p["side"]) for n, p in io.items()})

def post_route(d, net, summ):
    V = os.path.join(B, "verify"); out = os.path.join(R, "out"); rep = os.path.join(R, "reports")
    gds = os.path.join(out, f"{d}.gds")
    subprocess.run([sys.executable, os.path.join(V, "gaa3_drc.py"), gds], cwd=out, check=True, stdout=subprocess.DEVNULL)
    drc = json.load(open(os.path.join(out, f"{d}.drc.json")))
    subprocess.run([sys.executable, os.path.join(V, "gaa3_lvs.py"), gds, os.path.join(out, f"{d}_pnr.scs"), net["design"]], cwd=out, check=True, stdout=subprocess.DEVNULL)
    lvs = json.load(open(os.path.join(out, f"{d}.lvs.json")))
    subprocess.run([sys.executable, os.path.join(V, "gaa3_pex.py"), gds], cwd=out, check=True, stdout=subprocess.DEVNULL)
    pex = json.load(open(os.path.join(out, f"{d}.pex.json")))
    # post-route STA: wire-level extracted capacitance per net (device-level gate parasitics are in the .lib pin caps)
    wire2 = {n: (pex["nets"][n]["cgnd_wire_aF"] + pex["nets"][n]["ccoup_wire_aF"]) / 1e3 if n in pex["nets"] else 0.0 for n in net["nets"]}
    st = syn.reports(net, rep, d + "_postroute", wire_cap=wire2, break_at=net.get("break_at"), stage="postRoute")
    summ.update(drc_results=drc["total"], drc_rules=drc["checked"], lvs=lvs["result"], lvs_counts=dict(layout=lvs["layout"], schematic=lvs["schematic"]),
                pex_nets=pex["totals"]["nets"], pex_cgnd_fF=pex["totals"]["cgnd_aF"] / 1e3, pex_ccoup_fF=pex["totals"]["ccoup_aF"] / 1e3,
                postroute_path_ps=st["path_ps"], postroute_slack_ps=st["slack_ps"], postroute_power_uW=st["total_uW"])
    # Innovus-style log / summary
    Lg = [f"{'=' * 74}", f"  Innovus(TM) Implementation System  -  {net['design']}  flow summary", f"{'=' * 74}",
          f"  floorPlan     : 1 row gaa3_core, core {summ['core_w']} x {ROW_H} nm, target utilisation {UTIL:.2f}",
          f"  place_opt     : {summ['cells']} standard cells, {summ['fills']} fillers, utilisation {summ['utilisation']*100:.1f} %",
          f"  routeDesign   : {summ['nets']} signal nets on M2 tracks {summ['tracks_used']}, wirelength {summ['wirelength_nm']} nm, {summ['vias']} V1",
          f"  verify_drc    : {drc['total']} violations in {drc['checked']} rulechecks (GAA3_DRC)",
          f"  verifyConn    : LVS {lvs['result']} vs mapped netlist ({lvs['layout']['instances']} instances, {lvs['layout']['nets']} nets)",
          f"  extractRC     : {pex['totals']['nets']} nets, C_gnd {pex['totals']['cgnd_aF']/1e3:.3f} fF, C_coup {pex['totals']['ccoup_aF']/1e3:.3f} fF -> {d}.spef",
          f"  timeDesign    : postRoute path {st['path_ps'] if st['path_ps'] is not None else 'n/a (loop)'} ps, slack {st['slack_ps'] if st['slack_ps'] is not None else 'n/a'} ps vs vclk 200 ps",
          f"  streamOut     : {d}.gds ({len(summ['placed'])} cell references + routing), {d}.def", "=" * 74]
    open(os.path.join(rep, f"{d}_innovus.log"), "w").write("\n".join(Lg) + "\n")
    return summ

if __name__ == "__main__":
    os.makedirs(os.path.join(R, "out"), exist_ok=True); os.makedirs(os.path.join(R, "reports"), exist_ok=True)
    summary = {}
    for d in sys.argv[1:]:
        net = json.load(open(os.path.join(R, "out", f"{d}.json")))
        for last, flip in ((False, False), (False, True), (True, False), (True, True)):     # placement trials until the router succeeds
            placed, fills, core_w = place(net, obstructed_last=last, flip_obstructed=flip)
            try:
                routes, io = route(net, placed, core_w); break
            except RuntimeError as e:
                print(f"   {d}: {e} (obstructed_last={last}, flip={flip}) -> next placement trial")
        else:
            raise SystemExit(f"{d}: unroutable")
        summ = emit(net, placed, fills, core_w, routes, io, d)
        summ = post_route(d, net, summ)
        summary[d] = summ
        print(f"{d:10s} core {core_w}x{ROW_H} nm  cells {summ['cells']} fills {summ['fills']} util {summ['utilisation']*100:.0f}%  nets {summ['nets']} WL {summ['wirelength_nm']} nm vias {summ['vias']}  "
              f"DRC {summ['drc_results']}  LVS {summ['lvs']}  postRoute path {summ['postroute_path_ps']} ps")
    json.dump(summary, open(os.path.join(R, "reports", "pnr_summary.json"), "w"), indent=1)

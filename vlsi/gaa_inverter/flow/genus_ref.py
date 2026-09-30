#!/usr/bin/env python3
"""
genus_ref.py -- reference logic synthesis for the GAA3 flow (the Genus step of Fig. 5, run here without the tool).

  read_hdl   : the Verilog subset used by rtl/*.v (ANSI ports, parameters, vectors, assign with ~ & | ^ and
               parentheses, generate-for loops instantiating library cells)
  elaborate  : bit-blast vectors, unroll generate loops
  syn_map    : technology mapping onto INV_GAA_X1 / NAND2_GAA_X1 (NOT->INV, NAND->NAND2, AND->NAND2+INV,
               OR->NAND2 of inverted inputs), buffer removal
  reports    : report_gates, report_area, report_timing (NLDM STA from the .lib, loops broken at the
               enable gate as Genus does), report_power (leakage + switching at the SDC toggle rate)
  write_hdl / write_sdc / netlist JSON for the place-and-route step

    python3 genus_ref.py inverter nand2 ring_osc      -> out/<design>_netlist.v, out/<design>.json, reports/<design>_*.rpt
"""
import json, math, os, re, sys
R = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(R)
LIB = json.load(open(os.path.join(R, "lib", "char.json")))
AREA = {"INV_GAA_X1": 0.016128, "NAND2_GAA_X1": 0.024192}
LEAK = {"INV_GAA_X1": None, "NAND2_GAA_X1": None}
CIN = {"INV_GAA_X1": LIB["cin_inv_fF"], "NAND2_GAA_X1": LIB["cin_nand_fF"]}
WIRE_EST_FF = 0.02                      # pre-layout wire-load estimate per fanout (fF)
VCLK_PS, IO_DELAY_PS, PIN_LOAD_FF, MAX_TRAN_PS = 200.0, 20.0, 1.28, 15.0      # from genus/constraints.sdc
TOGGLE_HZ = 1e9                          # activity assumed by report_power (0.2 x 5 GHz)

# ------------------------------------------------------------------ Verilog subset front end
def read_hdl(path):
    src = re.sub(r"//.*", "", open(path).read()); src = re.sub(r"\(\*.*?\*\)", "", src, flags=re.S)
    m = re.search(r"module\s+(\w+)\s*(#\s*\((.*?)\))?\s*\((.*?)\)\s*;(.*)endmodule", src, re.S)
    name, params, ports, body = m.group(1), m.group(3) or "", m.group(4), m.group(5)
    P = {}
    for pm in re.finditer(r"parameter\s+(\w+)\s*=\s*(\d+)", params): P[pm.group(1)] = int(pm.group(2))
    inputs, outputs = [], []
    for pd in re.finditer(r"(input|output)\s+wire\s+(?:\[(\w+):(\w+)\]\s*)?(\w+)", ports):
        (outputs if pd.group(1) == "output" else inputs).append(pd.group(4))
    vectors = {}
    for vd in re.finditer(r"wire\s+\[(\w+):(\w+)\]\s*(\w+)\s*;", body):
        vectors[vd.group(3)] = (P.get(vd.group(1), int(vd.group(1)) if vd.group(1).isdigit() else 0), 0)
    assigns = [(a.group(1).strip(), a.group(2).strip()) for a in re.finditer(r"assign\s+(.*?)\s*=\s*(.*?);", body, re.S)]
    gens = []
    for g in re.finditer(r"for\s*\(\s*(\w+)\s*=\s*(\d+)\s*;\s*\1\s*<\s*(\w+)\s*;\s*\1\s*=\s*\1\s*\+\s*1\s*\)\s*begin\s*:\s*(\w+)(.*?)end\s*endgenerate", body, re.S):
        gens.append((g.group(1), int(g.group(2)), P.get(g.group(3), int(g.group(3)) if g.group(3).isdigit() else 0), g.group(4), g.group(5)))
    insts = re.findall(r"(\w+)\s+(\w+)\s*\(((?:\s*\.\w+\s*\([^)]*\)\s*,?)+)\)\s*;", body)
    return dict(name=name, params=P, inputs=inputs, outputs=outputs, vectors=vectors, assigns=assigns, gens=gens, insts=insts, body=body)

def bit(expr, env):
    """resolve an identifier / bit-select with constant arithmetic to a bit name"""
    expr = expr.strip()
    m = re.match(r"(\w+)\s*\[(.*)\]$", expr)
    if m:
        idx = eval(m.group(2), {}, env); return f"{m.group(1)}[{idx}]"
    return expr

def parse_expr(s):
    """tiny precedence parser: ~ > & > ^ > |"""
    s = s.strip()
    def tokens(s):
        return re.findall(r"~|&|\||\^|\(|\)|\w+(?:\s*\[[^\]]*\])?", s)
    toks = tokens(s); pos = [0]
    def peek(): return toks[pos[0]] if pos[0] < len(toks) else None
    def take(): pos[0] += 1; return toks[pos[0] - 1]
    def primary():
        t = take()
        if t == "(":
            e = expr_or(); take(); return e
        if t == "~": return ("NOT", primary())
        return ("ID", t)
    def expr_and():
        e = primary()
        while peek() == "&": take(); e = ("AND", e, primary())
        return e
    def expr_xor():
        e = expr_and()
        while peek() == "^": take(); e = ("XOR", e, expr_and())
        return e
    def expr_or():
        e = expr_xor()
        while peek() == "|": take(); e = ("OR", e, expr_xor())
        return e
    return expr_or()

# ------------------------------------------------------------------ elaboration + mapping
class Netlist:
    def __init__(self, name): self.name = name; self.insts = []; self.aliases = {}; self.k = 0
    def new_net(self): self.k += 1; return f"syn_net{self.k}"
    def add(self, cell, pins): self.insts.append(dict(name=f"g{len(self.insts)}", cell=cell, pins=pins)); return self.insts[-1]
    def resolve(self, n):
        while n in self.aliases: n = self.aliases[n]
        return n

def map_expr(nl, e, env, target=None):
    """returns the net carrying the value of e; if target is given, the result is placed on it"""
    kind = e[0]
    if kind == "ID":
        n = bit(e[1], env)
        if target: nl.aliases[target] = n; return n
        return n
    if kind == "NOT":
        inner = e[1]
        if inner[0] == "AND":                                   # ~(a & b) -> NAND2
            a = map_expr(nl, inner[1], env); b = map_expr(nl, inner[2], env); out = target or nl.new_net()
            nl.add("NAND2_GAA_X1", dict(A=a, B=b, Y=out)); return out
        a = map_expr(nl, inner, env); out = target or nl.new_net()
        nl.add("INV_GAA_X1", dict(A=a, Y=out)); return out
    if kind == "AND":                                            # NAND2 + INV
        a = map_expr(nl, e[1], env); b = map_expr(nl, e[2], env); t = nl.new_net(); out = target or nl.new_net()
        nl.add("NAND2_GAA_X1", dict(A=a, B=b, Y=t)); nl.add("INV_GAA_X1", dict(A=t, Y=out)); return out
    if kind == "OR":                                             # NAND2(~a, ~b)
        a = map_expr(nl, e[1], env); b = map_expr(nl, e[2], env); na, nb = nl.new_net(), nl.new_net(); out = target or nl.new_net()
        nl.add("INV_GAA_X1", dict(A=a, Y=na)); nl.add("INV_GAA_X1", dict(A=b, Y=nb)); nl.add("NAND2_GAA_X1", dict(A=na, B=nb, Y=out)); return out
    raise ValueError(kind)

def elaborate_and_map(h):
    nl = Netlist(h["name"]); env = dict(h["params"])
    for lhs, rhs in h["assigns"]:
        map_expr(nl, parse_expr(rhs), env, target=bit(lhs, env))
    for var, lo, hi, label, block in h["gens"]:
        for i in range(lo, hi):
            env2 = dict(env); env2[var] = i
            for cell, inst, conns in re.findall(r"(\w+)\s+(\w+)\s*\(((?:\s*\.\w+\s*\([^)]*\)\s*,?)+)\)\s*;", block):
                pins = {p: bit(v, env2) for p, v in re.findall(r"\.(\w+)\s*\(([^)]*)\)", conns)}
                nl.insts.append(dict(name=f"{label}[{i}]/{inst}", cell=cell, pins=pins))
    for inst in nl.insts:
        inst["pins"] = {p: nl.resolve(v) for p, v in inst["pins"].items()}
    ports = dict(inputs=list(h["inputs"]), outputs=[nl.resolve(o) if nl.resolve(o) != o else o for o in h["outputs"]])
    # an output that is an alias of an internal net keeps its port name: rename that net
    ren = {}
    for o in h["outputs"]:
        r = nl.resolve(o)
        if r != o: ren[r] = o
    for inst in nl.insts: inst["pins"] = {p: ren.get(v, v) for p, v in inst["pins"].items()}
    ports["outputs"] = list(h["outputs"])
    nets = sorted({v for inst in nl.insts for v in inst["pins"].values()} | set(ports["inputs"]) | set(ports["outputs"]))
    return dict(design=h["name"], ports=ports, insts=nl.insts, nets=nets)

# ------------------------------------------------------------------ STA on the NLDM tables
def interp(tab, slew_ps, load_ff):
    s, c = LIB["slews_ps"], LIB["loads_fF"]
    def idx(arr, v):
        if v <= arr[0]: return 0, 0.0
        if v >= arr[-1]: return len(arr) - 2, 1.0
        for i in range(len(arr) - 1):
            if arr[i] <= v <= arr[i + 1]: return i, (v - arr[i]) / (arr[i + 1] - arr[i])
    i, fs = idx(s, slew_ps); j, fc = idx(c, load_ff)
    v00, v01, v10, v11 = tab[i][j], tab[i][j + 1], tab[i + 1][j], tab[i + 1][j + 1]
    return (v00 * (1 - fs) + v10 * fs) * (1 - fc) + (v01 * (1 - fs) + v11 * fs) * fc

def arc(cell, pin, slew_ps, load_ff):
    t = LIB["inv"] if cell == "INV_GAA_X1" else LIB["nand"][pin]
    d = max(interp(t["cell_rise"], slew_ps, load_ff), interp(t["cell_fall"], slew_ps, load_ff))
    tr = max(interp(t["rise_transition"], slew_ps, load_ff), interp(t["fall_transition"], slew_ps, load_ff))
    return d, tr

def sta(net, wire_cap=None, break_at=None):
    """Longest path from any input to any output. wire_cap: extracted net capacitance (fF) or None (wireload)."""
    drivers = {inst["pins"]["Y"]: inst for inst in net["insts"]}
    loads = {}
    for inst in net["insts"]:
        for p, n in inst["pins"].items():
            if p != "Y": loads.setdefault(n, []).append((inst, p))
    def net_load(n):
        c = sum(CIN[i["cell"]] for i, _ in loads.get(n, []))
        if n in net["ports"]["outputs"]: c += PIN_LOAD_FF
        c += (wire_cap.get(n, 0.0) if wire_cap is not None else WIRE_EST_FF * max(len(loads.get(n, [])), 1))
        return c
    # arrival propagation (levelised; combinational loops are cut at the driver named in break_at)
    arr = {i: (IO_DELAY_PS, 12.0, [(i, "in", IO_DELAY_PS)]) for i in net["ports"]["inputs"]}
    visited = set(); order = []
    def inputs_of(d):          # at the loop-breaking instance only the primary-input pin is followed (Genus: loop cut)
        return [(p, m) for p, m in d["pins"].items() if p != "Y" and (d["name"] != break_at or m in net["ports"]["inputs"])]
    def visit(n, stack):
        if n in visited or n in stack: return
        d = drivers.get(n)
        if d is None: visited.add(n); return
        stack.add(n)
        for p, m in inputs_of(d): visit(m, stack)
        stack.discard(n); visited.add(n); order.append(n)
    for o in net["ports"]["outputs"]: visit(o, set())
    for inst in net["insts"]:
        visit(inst["pins"]["Y"], set())
    for n in order:
        d = drivers[n]; best = None
        for p, m in inputs_of(d):
            if m not in arr: continue
            t0, s0, path = arr[m]; dl, tr = arc(d["cell"], p, s0, net_load(n))
            if best is None or t0 + dl > best[0]: best = (t0 + dl, tr, path + [(n, f"{d['name']}/{p}->Y {d['cell']}", dl)])
        if best: arr[n] = best
    paths = []
    for o in net["ports"]["outputs"]:
        if o in arr: t, s, path = arr[o]; paths.append((t + IO_DELAY_PS, o, path, s, net_load(o)))
    paths.sort(reverse=True)
    return paths, net_load

def reports(net, outdir, prefix, wire_cap=None, break_at=None, stage="syn"):
    counts = {}
    for i in net["insts"]: counts[i["cell"]] = counts.get(i["cell"], 0) + 1
    area = sum(AREA[c] * n for c, n in counts.items())
    L = [f"{'=' * 74}", f"  Genus(TM) Synthesis Solution  -  report_gates   design {net['design']}   ({stage})", f"{'=' * 74}",
         f"  {'Gate':<16}{'Instances':>10}{'Area (um^2)':>14}   Library", "-" * 74]
    for c, n in sorted(counts.items()): L.append(f"  {c:<16}{n:>10}{AREA[c]*n:>14.6f}   gaa3_stdcells_tt_0p70v_25c")
    L += ["-" * 74, f"  {'total':<16}{sum(counts.values()):>10}{area:>14.6f}", "", f"  Nets: {len(net['nets'])}   Ports: {len(net['ports']['inputs'])} in / {len(net['ports']['outputs'])} out", "=" * 74]
    open(os.path.join(outdir, f"{prefix}_gates.rpt"), "w").write("\n".join(L) + "\n")
    paths, net_load = sta(net, wire_cap, break_at)
    T = [f"{'=' * 74}", f"  report_timing  design {net['design']}   ({stage}, {'extracted RC' if wire_cap else 'wire-load estimate'})", f"{'=' * 74}"]
    if paths:
        t, o, path, s, cl = paths[0]; slack = VCLK_PS - t
        T += [f"  Path 1: {'MET' if slack >= 0 else 'VIOLATED'} ({slack:.1f} ps)  Setup check with pin {o} against virtual clock vclk (period {VCLK_PS:.0f} ps)",
              f"  Startpoint: {path[0][0]} (input port, input delay {IO_DELAY_PS:.0f} ps)   Endpoint: {o} (output port, output delay {IO_DELAY_PS:.0f} ps)",
              f"  Required time {VCLK_PS - IO_DELAY_PS:.1f} ps   Arrival {t - IO_DELAY_PS:.2f} ps   Slack {slack:.2f} ps", "-" * 74,
              f"  {'Pin / arc':<40}{'Cell':<14}{'Delay':>8}{'Arrival':>9}", "-" * 74]
        acc = 0.0
        for n, what, dl in path:
            acc += dl; cellname = what.split()[-1] if "->" in what else ""
            T.append(f"  {(what if '->' in what else n + ' (' + what + ')'):<40}{cellname:<14}{dl:>8.2f}{acc:>9.2f}")
        T += ["-" * 74, f"  Data arrival at {o}: {acc:.2f} ps    output slew {s:.2f} ps    load {cl:.3f} fF"]
    else:
        T.append("  No constrained path (combinational loop broken; see report_timing -unconstrained)")
    T.append("=" * 74)
    open(os.path.join(outdir, f"{prefix}_timing.rpt"), "w").write("\n".join(T) + "\n")
    # power
    leak_inv = json.load(open(os.path.join(B, "spectre", "results.json")))["P_static_pW"]
    leak_nand = json.load(open(os.path.join(B, "spectre", "results_nand2.json")))["P_static_avg_pW"]
    leak = counts.get("INV_GAA_X1", 0) * leak_inv + counts.get("NAND2_GAA_X1", 0) * leak_nand
    e_inv = json.load(open(os.path.join(B, "spectre", "results_postlayout.json")))["inverter"]["post"]["E_cycle"]
    sw = 0.0; internal = 0.0
    for i in net["insts"]:
        cl = net_load(i["pins"]["Y"]) * 1e-15
        sw += cl * 0.7 ** 2 * TOGGLE_HZ                          # C V^2 f per full cycle (rise + fall)
        internal += (0.15e-15 + (0.16e-15 if i["cell"] == "NAND2_GAA_X1" else 0)) * 0.7 ** 2 * TOGGLE_HZ + 0.05 * e_inv * TOGGLE_HZ
    P = [f"{'=' * 74}", f"  report_power  design {net['design']}   ({stage}; toggle rate {TOGGLE_HZ/1e9:.1f} GHz on every net)", f"{'=' * 74}",
         f"  {'Category':<20}{'Leakage (nW)':>14}{'Internal (uW)':>15}{'Switching (uW)':>16}{'Total (uW)':>12}", "-" * 74,
         f"  {'combinational':<20}{leak/1e3:>14.3f}{internal*1e6:>15.4f}{sw*1e6:>16.4f}{(leak*1e-12 + internal + sw)*1e6:>12.4f}", "=" * 74]
    open(os.path.join(outdir, f"{prefix}_power.rpt"), "w").write("\n".join(P) + "\n")
    return dict(cells=sum(counts.values()), counts=counts, area_um2=area, nets=len(net["nets"]),
                path_ps=(paths[0][0] - 2 * IO_DELAY_PS) if paths else None, slack_ps=(VCLK_PS - paths[0][0]) if paths else None,
                leakage_nW=leak / 1e3, dynamic_uW=(internal + sw) * 1e6, total_uW=(leak * 1e-12 + internal + sw) * 1e6)

def write_hdl(net, path):
    L = [f"// {net['design']}_netlist.v -- mapped by genus_ref.py onto gaa3_stdcells_tt_0p70v_25c", f"module {net['design']} ({', '.join(net['ports']['inputs'] + net['ports']['outputs'])});"]
    for i in net["ports"]["inputs"]: L.append(f"  input {i};")
    for o in net["ports"]["outputs"]: L.append(f"  output {o};")
    ports = set(net["ports"]["inputs"] + net["ports"]["outputs"])
    for n in net["nets"]:
        if n not in ports: L.append(f"  wire \\{n} ;" if "[" in n else f"  wire {n};")
    for inst in net["insts"]:
        esc = lambda v: ("\\" + v + " ") if "[" in v else v
        conns = ", ".join(f".{p}({esc(v)})" for p, v in inst["pins"].items())
        nm = ("\\" + inst["name"] + " ") if "/" in inst["name"] or "[" in inst["name"] else inst["name"]
        L.append(f"  {inst['cell']} {nm} ({conns});")
    L.append("endmodule")
    open(path, "w").write("\n".join(L) + "\n")

if __name__ == "__main__":
    os.makedirs(os.path.join(R, "out"), exist_ok=True); os.makedirs(os.path.join(R, "reports"), exist_ok=True)
    summary = {}
    for d in sys.argv[1:]:
        h = read_hdl(os.path.join(B, "rtl", d + ".v"))
        net = elaborate_and_map(h)
        brk = next((i["name"] for i in net["insts"] if i["cell"] == "NAND2_GAA_X1" and "en" in i["pins"].values()), None) if d == "ring_osc" else None
        net["break_at"] = brk
        s = reports(net, os.path.join(R, "reports"), d, break_at=brk)
        write_hdl(net, os.path.join(R, "out", f"{d}_netlist.v"))
        json.dump(net, open(os.path.join(R, "out", f"{d}.json"), "w"), indent=1)
        summary[d] = s
        print(f"{d:10s} cells={s['cells']} {s['counts']} area={s['area_um2']:.4f} um2 nets={s['nets']} path={s['path_ps']} ps slack={s['slack_ps']} ps  P={s['total_uW']:.3f} uW")
    json.dump(summary, open(os.path.join(R, "reports", "synthesis_summary.json"), "w"), indent=1)

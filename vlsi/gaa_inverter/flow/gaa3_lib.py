#!/usr/bin/env python3
"""
gaa3_lib.py -- characterises INV_GAA_X1 and NAND2_GAA_X1 with the post-layout reference model and writes
the GAA3 standard-cell library views used by the digital flow:
  gaa3_stdcells_tt_0p70v_25c.lib   Liberty NLDM (delay / output-transition tables vs input slew and load,
                                   pin capacitance from extraction, leakage and switching energy)
  gaa3_tech.lef                    technology LEF (site, routing layers M1-M4 with pitch/width/spacing, vias)
  gaa3_stdcells.lef                cell abstracts (SIZE, PIN ports on M1, OBS), plus FILL_GAA_X1
Run: python3 gaa3_lib.py   (from vlsi/gaa_inverter/flow)
"""
import json, os, sys
R = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(R)
sys.path.insert(0, os.path.join(B, "spectre")); os.chdir(os.path.join(B, "spectre"))
import ref_model as rm, nand2 as nd, postlayout as pl

V = rm.VDD
SLEWS = [6e-12, 12e-12, 24e-12]                     # input 10-90 % slews (Liberty index_1, ps)
LOADS = [0.33e-15, 0.66e-15, 1.32e-15, 2.64e-15]    # loads (index_2, fF): 0.5x, 1x, 2x, 4x post-layout INV input cap

def slew(ts, v, rising, tstart, lo=0.2, hi=0.8):
    def cross(level, rising_):
        for i in range(1, len(ts)):
            if ts[i] < tstart: continue
            a, b = v[i - 1], v[i]
            if (rising_ and a < level <= b) or (not rising_ and a > level >= b):
                return ts[i - 1] + (level - a) / (b - a) * (ts[i] - ts[i - 1])
        return float("nan")
    return abs(cross(hi * V, rising) - cross(lo * V, rising))

def char_inv(pex):
    Y = pex["nets"]["Y"]; cout = Y["cgnd_aF"] * 1e-18; cc = Y["coup_aF"].get("A", 0) * 1e-18; rout = 0.5 * Y["r_ohm"]
    tab = {k: [[0.0] * len(LOADS) for _ in SLEWS] for k in ("cell_fall", "cell_rise", "fall_transition", "rise_transition")}
    energy = [[0.0] * len(LOADS) for _ in SLEWS]
    for i, s in enumerate(SLEWS):
        for j, c in enumerate(LOADS):
            r = pl.tran_inv(c, cout, cc, rout, tr=s)
            w = r["wave"]
            tab["cell_fall"][i][j] = r["tpHL"] * 1e12; tab["cell_rise"][i][j] = r["tpLH"] * 1e12
            tab["fall_transition"][i][j] = slew(w["t"], w["vout"], False, 5e-12) * 1e12
            tab["rise_transition"][i][j] = slew(w["t"], w["vout"], True, 40e-12) * 1e12
            energy[i][j] = r["E_cycle"]
    return tab, energy

def char_nand(pex):
    Yn = pex["nets"]["Y"]; X = next(v for k, v in pex["nets"].items() if k.startswith("int"))
    cout = Yn["cgnd_aF"] * 1e-18 + Yn["coup_aF"].get(next(k for k in pex["nets"] if k.startswith("int")), 0) * 1e-18
    cx = X["cgnd_aF"] * 1e-18 + (X["coup_aF"].get("A", 0) + X["coup_aF"].get("B", 0)) * 1e-18
    cca, ccb = Yn["coup_aF"].get("A", 0) * 1e-18, Yn["coup_aF"].get("B", 0) * 1e-18; rout = 0.5 * Yn["r_ohm"]
    arcs = {}
    for mode in ("A", "B"):
        tab = {k: [[0.0] * len(LOADS) for _ in SLEWS] for k in ("cell_fall", "cell_rise", "fall_transition", "rise_transition")}
        energy = [[0.0] * len(LOADS) for _ in SLEWS]
        for i, s in enumerate(SLEWS):
            for j, c in enumerate(LOADS):
                r = pl.tran_nand(mode, c, cout, cca, ccb, cx, rout, tr=s); w = r["wave"]
                tab["cell_fall"][i][j] = r["tpHL"] * 1e12; tab["cell_rise"][i][j] = r["tpLH"] * 1e12
                tab["fall_transition"][i][j] = slew(w["t"], w["vout"], False, 5e-12) * 1e12
                tab["rise_transition"][i][j] = slew(w["t"], w["vout"], True, 40e-12) * 1e12
                energy[i][j] = r["E_cycle"]
        arcs[mode] = (tab, energy)
    return arcs

def lut(name, tab):
    idx1 = ", ".join(f"{s*1e12:.1f}" for s in SLEWS); idx2 = ", ".join(f"{c*1e15:.3f}" for c in LOADS)
    rows = ", \\\n            ".join('"' + ", ".join(f"{v:.4f}" for v in row) + '"' for row in tab)
    return f'''        {name}(delay_template_3x4) {{
          index_1("{idx1}");
          index_2("{idx2}");
          values({rows});
        }}'''

def timing_group(related, tab, energy, when=None):
    e_avg = sum(sum(r) for r in energy) / (len(SLEWS) * len(LOADS))
    return f'''      timing() {{
        related_pin : "{related}";
        timing_sense : negative_unate;
{lut("cell_rise", tab["cell_rise"])}
{lut("cell_fall", tab["cell_fall"])}
{lut("rise_transition", tab["rise_transition"])}
{lut("fall_transition", tab["fall_transition"])}
      }}
      internal_power() {{
        related_pin : "{related}";
        rise_power(power_template_3x4) {{ index_1("{", ".join(f"{s*1e12:.1f}" for s in SLEWS)}"); index_2("{", ".join(f"{c*1e15:.3f}" for c in LOADS)}");
          values({", ".join('"' + ", ".join(f"{(energy[i][j] - LOADS[j] * V * V) * 0.5 * 1e15:.4f}" for j in range(len(LOADS))) + '"' for i in range(len(SLEWS)))}); }}
        fall_power(power_template_3x4) {{ index_1("{", ".join(f"{s*1e12:.1f}" for s in SLEWS)}"); index_2("{", ".join(f"{c*1e15:.3f}" for c in LOADS)}");
          values({", ".join('"' + ", ".join(f"{(energy[i][j] - LOADS[j] * V * V) * 0.5 * 1e15:.4f}" for j in range(len(LOADS))) + '"' for i in range(len(SLEWS)))}); }}
      }}'''

def liberty(inv_tab, inv_e, nand_arcs, cin_inv, cin_nand, leak_inv, leak_nand):
    hdr = f'''library(gaa3_stdcells_tt_0p70v_25c) {{
  comment : "GAA3 generic 3-nm-class nanosheet library, characterised with the post-layout reference model (gaa3_lib.py)";
  technology(cmos); delay_model : table_lookup;
  time_unit : "1ps"; voltage_unit : "1V"; current_unit : "1uA"; leakage_power_unit : "1pW"; capacitive_load_unit(1, ff); pulling_resistance_unit : "1kohm";
  nom_process : 1.0; nom_temperature : 25.0; nom_voltage : 0.70;
  operating_conditions(tt_0p70v_25c) {{ process : 1.0; temperature : 25.0; voltage : 0.70; tree_type : "balanced_tree"; }}
  default_operating_conditions : tt_0p70v_25c;
  slew_lower_threshold_pct_rise : 20.0; slew_upper_threshold_pct_rise : 80.0; slew_lower_threshold_pct_fall : 20.0; slew_upper_threshold_pct_fall : 80.0;
  input_threshold_pct_rise : 50.0; input_threshold_pct_fall : 50.0; output_threshold_pct_rise : 50.0; output_threshold_pct_fall : 50.0;
  default_max_transition : 30.0; default_fanout_load : 1.0;
  lu_table_template(delay_template_3x4) {{ variable_1 : input_net_transition; variable_2 : total_output_net_capacitance; index_1("6, 12, 24"); index_2("0.33, 0.66, 1.32, 2.64"); }}
  power_lu_template(power_template_3x4) {{ variable_1 : input_net_transition; variable_2 : total_output_net_capacitance; index_1("6, 12, 24"); index_2("0.33, 0.66, 1.32, 2.64"); }}
  cell(INV_GAA_X1) {{
    area : 0.016128; cell_leakage_power : {leak_inv:.2f};
    pin(A) {{ direction : input; capacitance : {cin_inv:.4f}; }}
    pin(Y) {{ direction : output; function : "!A"; max_capacitance : 4.0;
{timing_group("A", inv_tab, inv_e)}
    }}
    pin(VDD) {{ direction : inout; pg_type : primary_power; }} pin(VSS) {{ direction : inout; pg_type : primary_ground; }}
  }}
  cell(NAND2_GAA_X1) {{
    area : 0.024192; cell_leakage_power : {leak_nand:.2f};
    pin(A) {{ direction : input; capacitance : {cin_nand:.4f}; }}
    pin(B) {{ direction : input; capacitance : {cin_nand:.4f}; }}
    pin(Y) {{ direction : output; function : "!(A B)"; max_capacitance : 4.0;
{timing_group("A", *nand_arcs["A"])}
{timing_group("B", *nand_arcs["B"])}
    }}
    pin(VDD) {{ direction : inout; pg_type : primary_power; }} pin(VSS) {{ direction : inout; pg_type : primary_ground; }}
  }}
  cell(FILL_GAA_X1) {{ area : 0.008064; cell_leakage_power : 0.0; dont_touch : true; dont_use : true;
    pin(VDD) {{ direction : inout; pg_type : primary_power; }} pin(VSS) {{ direction : inout; pg_type : primary_ground; }} }}
}}
'''
    return hdr

def lefs():
    tech = '''VERSION 5.8 ;
BUSBITCHARS "[]" ; DIVIDERCHAR "/" ;
UNITS DATABASE MICRONS 1000 ; END UNITS
MANUFACTURINGGRID 0.001 ;
SITE gaa3_core CLASS CORE ; SYMMETRY Y ; SIZE 0.048 BY 0.168 ; END gaa3_core
LAYER M1 TYPE ROUTING ; DIRECTION VERTICAL ; PITCH 0.028 ; WIDTH 0.016 ; SPACING 0.012 ; RESISTANCE RPERSQ 22 ; CAPACITANCE CPERSQDIST 0.0003 ; END M1
LAYER V1 TYPE CUT ; SPACING 0.012 ; WIDTH 0.010 ; RESISTANCE 35 ; END V1
LAYER M2 TYPE ROUTING ; DIRECTION HORIZONTAL ; PITCH 0.028 ; WIDTH 0.016 ; SPACING 0.012 ; RESISTANCE RPERSQ 18 ; CAPACITANCE CPERSQDIST 0.00018 ; END M2
LAYER V2 TYPE CUT ; SPACING 0.012 ; WIDTH 0.010 ; RESISTANCE 30 ; END V2
LAYER M3 TYPE ROUTING ; DIRECTION VERTICAL ; PITCH 0.028 ; WIDTH 0.016 ; SPACING 0.012 ; RESISTANCE RPERSQ 15 ; END M3
LAYER V3 TYPE CUT ; SPACING 0.014 ; WIDTH 0.012 ; RESISTANCE 25 ; END V3
LAYER M4 TYPE ROUTING ; DIRECTION HORIZONTAL ; PITCH 0.036 ; WIDTH 0.020 ; SPACING 0.016 ; RESISTANCE RPERSQ 12 ; END M4
VIA V1_M1M2 DEFAULT LAYER M1 ; RECT -0.008 -0.008 0.008 0.008 ; LAYER V1 ; RECT -0.005 -0.005 0.005 0.005 ; LAYER M2 ; RECT -0.008 -0.008 0.008 0.008 ; END V1_M1M2
VIA V2_M2M3 DEFAULT LAYER M2 ; RECT -0.008 -0.008 0.008 0.008 ; LAYER V2 ; RECT -0.005 -0.005 0.005 0.005 ; LAYER M3 ; RECT -0.008 -0.008 0.008 0.008 ; END V2_M2M3
END LIBRARY
'''
    def pin(name, use, dirn, rects, layer="M1"):
        r = " ".join(f"RECT {x0/1e3:.3f} {y0/1e3:.3f} {x1/1e3:.3f} {y1/1e3:.3f} ;" for x0, y0, x1, y1 in rects)
        return f"  PIN {name} DIRECTION {dirn} ; USE {use} ; PORT LAYER {layer} ; {r} END END {name}\n"
    cells = "VERSION 5.8 ;\nBUSBITCHARS \"[]\" ; DIVIDERCHAR \"/\" ;\n"
    cells += "MACRO INV_GAA_X1 CLASS CORE ; ORIGIN 0 0 ; FOREIGN INV_GAA_X1 0 0 ; SIZE 0.096 BY 0.168 ; SYMMETRY X Y ; SITE gaa3_core ;\n"
    cells += pin("A", "SIGNAL", "INPUT", [(39, 76, 55, 92)]) + pin("Y", "SIGNAL", "OUTPUT", [(67, 34, 83, 134)])
    cells += pin("VDD", "POWER", "INOUT", [(0, 156, 96, 180)]) + pin("VSS", "GROUND", "INOUT", [(0, -12, 96, 12)])
    cells += "  OBS LAYER M1 ; RECT 0.016 0.000 0.032 0.064 ; RECT 0.016 0.104 0.032 0.168 ; END\nEND INV_GAA_X1\n"
    cells += "MACRO NAND2_GAA_X1 CLASS CORE ; ORIGIN 0 0 ; FOREIGN NAND2_GAA_X1 0 0 ; SIZE 0.144 BY 0.168 ; SYMMETRY X Y ; SITE gaa3_core ;\n"
    cells += pin("A", "SIGNAL", "INPUT", [(40, 76, 56, 92)]) + pin("B", "SIGNAL", "INPUT", [(84, 76, 100, 92)]) + pin("Y", "SIGNAL", "OUTPUT", [(112, 76, 128, 92)], "M2")
    cells += pin("VDD", "POWER", "INOUT", [(0, 156, 144, 180)]) + pin("VSS", "GROUND", "INOUT", [(0, -12, 144, 12)])
    cells += "  OBS LAYER M1 ; RECT 0.016 0.000 0.032 0.069 ; RECT 0.016 0.104 0.032 0.168 ; RECT 0.112 0.024 0.128 0.092 ; RECT 0.112 0.104 0.128 0.168 ; LAYER M2 ; RECT 0.064 0.111 0.128 0.127 ; RECT 0.112 0.076 0.128 0.127 ; END\nEND NAND2_GAA_X1\n"
    cells += "MACRO FILL_GAA_X1 CLASS CORE SPACER ; ORIGIN 0 0 ; FOREIGN FILL_GAA_X1 0 0 ; SIZE 0.048 BY 0.168 ; SYMMETRY X Y ; SITE gaa3_core ;\n"
    cells += pin("VDD", "POWER", "INOUT", [(0, 156, 48, 180)]) + pin("VSS", "GROUND", "INOUT", [(0, -12, 48, 12)]) + "END FILL_GAA_X1\nEND LIBRARY\n"
    return tech, cells

if __name__ == "__main__":
    pinv = pl.pex("gaa_inverter"); pnand = pl.pex("gaa_nand2")
    inv_tab, inv_e = char_inv(pinv); nand_arcs = char_nand(pnand)
    plr = json.load(open("results_postlayout.json"))
    cin_inv = plr["inverter"]["Cin_post_fF"]; cin_nand = plr["nand2"]["Cin_post_fF"]
    leak_inv = json.load(open("results.json"))["P_static_pW"]; leak_nand = json.load(open("results_nand2.json"))["P_static_avg_pW"]
    lib = liberty(inv_tab, inv_e, nand_arcs, cin_inv, cin_nand, leak_inv, leak_nand)
    tech, cells = lefs()
    os.makedirs(os.path.join(R, "lib"), exist_ok=True)
    open(os.path.join(R, "lib", "gaa3_stdcells_tt_0p70v_25c.lib"), "w").write(lib)
    open(os.path.join(R, "lib", "gaa3_tech.lef"), "w").write(tech); open(os.path.join(R, "lib", "gaa3_stdcells.lef"), "w").write(cells)
    json.dump(dict(slews_ps=[s * 1e12 for s in SLEWS], loads_fF=[c * 1e15 for c in LOADS], inv=inv_tab, nand=dict(A=nand_arcs["A"][0], B=nand_arcs["B"][0]),
                   cin_inv_fF=cin_inv, cin_nand_fF=cin_nand), open(os.path.join(R, "lib", "char.json"), "w"), indent=1)
    print("INV cell_fall (ps) rows=slew 6/12/24, cols=load 0.33/0.66/1.32/2.64 fF:")
    for row in inv_tab["cell_fall"]: print("   ", [round(v, 2) for v in row])
    print("NAND2 A-arc cell_rise:", [round(v, 2) for v in nand_arcs["A"][0]["cell_rise"][1]])
    print("library written: flow/lib/")

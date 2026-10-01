# HANDOVER — GAA Nanosheet Inverter / NAND2 / RO / SRAM: Cadence RTL-to-GDSII study and Q1 manuscript

Written 2026-10-01 at the end of the session that produced everything under `vlsi/gaa_inverter/`.
Read this first if you are a new model or a new person continuing the work.

---

## 1. Who this is for and what they want

**Owner:** Dr. M. Nisha Angeline, Professor and Head, Department of ECE, Velalar College of Engineering
and Technology, Thindal, Erode. Research interests: plasma technology, quantum computing, biomedical
devices, VLSI / advanced chip technology, antenna design (HFSS), open-source tools. Goal of this work:
a **Q1-journal manuscript** on a gate-all-around (GAA) nanosheet CMOS design flow run in **Cadence
(Virtuoso / Spectre / Genus / Innovus / Pegasus / Quantus) inside a VMware Workstation guest**, with
GDSII deliverables for every circuit.

**Repository / branch:** `nishaangelinem-coder/Plasma-Catalyst-Microreactor-Digital-Twin`, branch
`claude/serene-volta-653g3f`. The rest of the repository is an unrelated plasma-microreactor digital
twin; everything for this work lives in `vlsi/gaa_inverter/`. All work is committed and pushed.

**Published manuscript page (artifact):** https://claude.ai/artifact/N5DafgFFfvD6W2XEqr6y2J
(private; the owner shares it from the page's Share menu). Source file:
`vlsi/gaa_inverter/docs/gaa_inverter_paper.html`, built by `docs/build_page.py` from
`docs/template.html`. **To update the page: rebuild, then publish the same file path** (from this
session) or pass that URL as `url` from another session (read it first).

---

## 2. The one rule that shaped everything: honesty about provenance

Cadence is **not** available in the cloud session. Instead of faking tool output, every step has a
**reference implementation in Python** that produces the same deliverable the tool would, and the
paper says so in every caption, status bar ("ref. model" / "ref. checker" / "ref. flow") and in a
provenance box at the top of Section IV. The sign-off run in the VMware guest is expected to **replace**
the reference numbers and the tool-style renderings. Keep this discipline: never present a rendering
as a screenshot, never present a model number as a measured one.

What is real and what is reference:

| Item | Status |
|---|---|
| GDSII files (inverter, NAND2, RO11, SRAM6T, routed designs) | **Real** Calma GDSII, written by a dependency-free writer, validated by gdstk read-back |
| DRC / LVS / PEX on those GDSII files | **Real checks** by reference scripts (gdstk booleans), own 26-rule deck; not a foundry deck |
| Electrical numbers (VTC, delays, RO, SRAM, post-layout) | **Reference compact model** calibrated to IRDS 3-nm targets; replace with Spectre/BSIM-CMG |
| Liberty / LEF / synthesis / P&R / DEF / SPEF | **Real files** produced by reference scripts; replace with Genus/Innovus/Quantus outputs |
| Tool-style figures (Virtuoso, ViVA, Pegasus, Quantus, Innovus, Genus windows) | **Renderings in the tool's convention**, drawn from the reference result files |
| Cadence scripts (`.scs`, Genus/Innovus TCL, QRC `.ccl`, SKILL stream-out) | Written to run in the guest; **not executed here** |

---

## 3. Directory map (`vlsi/gaa_inverter/`)

```
README.md                 how to run everything (VMware setup, Cadence commands, reference commands)
rtl/                      inverter.v, nand2.v, ring_osc.v (+ testbenches)         -> Xcelium / Genus input
spectre/                  BSIM-CMG testbenches (gaa_inv_tb.scs, gaa_nand2_tb.scs, gaa_ro11_tb.scs, gaa_sram6t_tb.scs)
                          ref_model.py (compact model), nand2.py, ro.py, sram6t.py, postlayout.py
                          results*.json, fig_*.svg (page charts)
genus/                    synth.tcl, synth_ro.tcl, constraints.sdc              -> Genus (guest)
innovus/                  pnr.tcl, mmmc.tcl                                     -> Innovus (guest)
layout/                   gen_gaa_inverter_gds.py (GDSII writer + INV cell), gen_gaa_nand2_gds.py,
                          gen_gaa_ro_gds.py, gen_gaa_sram6t_gds.py, gaa3.layermap, streamout_virtuoso.il
                          *.gds (deliverables), *.svg (renderings)
verify/                   gaa3_drc.py (26-rule deck), gaa3_lvs.py (extractor+comparator), gaa3_pex.py (RC + SPEF),
                          gaa3_qrc.ccl (Quantus cmd), ro11_sch.scs, run_all.sh, *.drc.sum, *.lvs.rpt, *.pex.sum, *.spef
flow/                     gaa3_lib.py (Liberty/LEF), genus_ref.py (synthesis), innovus_ref.py (P&R + sign-off)
                          lib/ (.lib, .lef, char.json)  out/ (netlists, DEF, GDS, reports)  reports/ (rpt, json)
docs/                     template.html (manuscript with {PLACEHOLDERS}), build_page.py (fills them),
                          gen_schematics.py, gen_schematics_virtuoso.py, gen_viva.py, gen_verif_views.py,
                          gen_flow_views.py, render_pngs.py, figures/ (all SVG + PNG, README.md)
                          gaa_inverter_paper.html (built page)
```

---

## 4. Regeneration order (run from `vlsi/gaa_inverter/`; Python 3, `pip install gdstk`)

```bash
# 1. cell layouts + DRC + LVS (all four cells)            -> layout/*.gds, verify/*.drc.sum, *.lvs.rpt
./verify/run_all.sh
# 2. parasitic extraction                                  -> verify/*.pex.json, *.spef, gaa3_pex_all.sum
cd verify && python3 gaa3_pex.py ../layout/gaa_inverter.gds ../layout/gaa_nand2.gds ../layout/gaa_ro11.gds ../layout/gaa_sram6t.gds \
  && cat gaa_inverter.pex.sum gaa_nand2.pex.sum gaa_ro11.pex.sum gaa_sram6t.pex.sum > gaa3_pex_all.sum && cd ..
# 3. reference electrical results (order matters: FinFET variants first where a figure compares both)
cd spectre && python3 ref_model.py && GAA_TECH=finfet python3 ref_model.py \
  && python3 ro.py && GAA_TECH=finfet python3 ro.py && python3 ro.py --figs \
  && python3 nand2.py && GAA_TECH=finfet python3 nand2.py \
  && GAA_TECH=finfet python3 sram6t.py && python3 sram6t.py \
  && python3 postlayout.py && cd ..
# 4. digital flow                                          -> flow/lib, flow/out, flow/reports
cd flow && python3 gaa3_lib.py && python3 genus_ref.py inverter nand2 ring_osc && python3 innovus_ref.py inverter nand2 ring_osc && cd ..
# 5. figures (SVG) and PNG renders, then the page
cd docs && python3 gen_schematics.py && python3 gen_schematics_virtuoso.py && python3 gen_viva.py \
  && python3 gen_verif_views.py && python3 gen_flow_views.py && python3 render_pngs.py && python3 build_page.py
```
Runtimes: ro.py ~1-2 min per technology, sram6t ~1 min, postlayout ~1 min, innovus_ref ~2 min, render_pngs ~3 min.
`render_pngs.py` needs the headless Chromium at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`
(override with `CHROME=...`).

---

## 5. How the manuscript page is built

* `docs/template.html` holds the full text with `{NAME}` placeholders; `docs/build_page.py` fills them from
  the JSON results and inlines every SVG figure and every listed script as a `<pre>` listing.
  `build_page.py` asserts that no placeholder is left; a failure names the missing one.
* **Figure and table numbers are hard-coded in the template** (captions `<b>Fig. N.</b>` and in-text
  `Fig. N`). Inserting a figure in the middle = shift all later numbers: the sessions did it with
  `re.sub(r"Fig\. (\d+)", ...)` on the template. Tables use Roman numerals, same approach.
* Listings are the `LISTINGS` list in `build_page.py` (number, path, title, collapsed?). Add new scripts there.
* Current structure: Sections I-VI; Section III (methodology) has Figs. 2-5 (schematics, Virtuoso-style
  schematics, inverter layout, flow); Section IV has subsections A-K:
  A device, B VTC, C transient (+ Fig. 9 ViVA panels), D GDSII verification, E FinFET comparison (Table V),
  F ring oscillator (Table VI), G NAND2 (Table VII), H SRAM (Table VIII), I DRC/LVS (Tables IX-X, Figs. 16-17),
  J PEX/post-layout (Tables XI-XII, Figs. 18-19), K RTL-to-GDSII (Tables XIII-XIV, Figs. 20-21).
  Figures run 1-21, tables I-XIV, listings 1-46.
* Page design: journal manuscript, light/dark theme tokens in `:root`, fonts Newsreader / Source Serif 4 /
  IBM Plex, charts are hover-interactive SVGs (data in `data-series` attributes; JS at the end of the template).
  Chart colours: `--c1 #2a78d6`, `--c2 #eb6834` (validated palette). Keep one y-axis per chart.
* Author line: "M. Nisha Angeline, Professor and Head" (do not add credentials that were not given).
  Masthead says "Manuscript prepared for Q1 journal submission" (no invented journal name).

---

## 6. Key design facts (keep consistent if you change anything)

**Technology (generic "GAA3", 3-nm class):** Lg 14 nm, CPP 48 nm, 3 sheets × 5 nm, EOT 0.9 nm, VDD 0.7 V,
6-track cell 168 nm (M1/M2 pitch 28, width 16, spacing 12), rails 24 nm, V0/V1 10 nm, 1-nm database unit.
Layer map (`layout/gaa3.layermap`): NWELL 1, NSHEET 2 (2:1 stack mark), GATE 3 (3:1 cut), SDC 4, CB 5,
V0 6, M1 7 (7:1 pin, 7:2 text, 7:3 net name), V1 8, M2 9 (9:1/9:2/9:3), V2 10, M3 11, boundary 235.

**Cells:** INV_GAA_X1 96×168 (N 30-nm / P 45-nm sheets); NAND2_GAA_X1 144×168 (N 45 / P 30, series stack,
output on M2 above the pin level only); RO11_GAA 1056×168 (11 SREFs + M2 wiring);
SRAM6T_GAA_HD 216×96 thin cell (PD 36 / PG 24 / PU 20-nm sheets, butted-contact cross-coupling, M2 BL/BLB/VDD/VSS, M3 WL).
All four: DRC clean (26 rules), LVS MATCH, extracted to SPEF.

**Reference model** (`spectre/ref_model.py`): EKV-style unified current with α=1.25, DIBL-like λ;
NMOS Vth 0.24 V SS 68, PMOS 0.26 V SS 70; Ion 1.00/0.75 mA/µm of W_eff; W_eff = 3·2·(W+5) nm.
Calibration constant is computed **eagerly at VDD_NOM = 0.7 V** (see pitfalls). FinFET baseline via `GAA_TECH=finfet`.

**Headline numbers (reference model, 0.7 V):**

| Metric | GAA | FinFET baseline |
|---|---|---|
| Inverter FO4 tpd / E per cycle (pre-layout) | 5.77 ps / 0.84 fJ | 6.85 ps / 0.80 fJ |
| Inverter FO4 tpd (post-layout, extracted RC) | 8.42 ps | – |
| VM / gain / NM_L / NM_H | 350 mV / 28 / 255 / 266 mV | 335 mV / 28 |
| RO11 FO3 f / stage delay (pre-layout) | 12.05 GHz / 3.77 ps | 9.11 GHz / 4.99 ps |
| RO11 post-layout | 7.18 GHz / 6.33 ps | – |
| NAND2 worst arc (pre / post) | 7.60 / 9.39 ps | 8.66 ps |
| SRAM hold / read SNM, write trip, I_read | 254 / 105 mV, 293 mV, 112 µA | 266 / 94 mV, 294 mV, 51 µA |
| Inverter Cin pre / post | 0.32 / 0.66 fF | – |
| ring_osc design (13 cells) post-route en→out path | 49.2 ps, slack 110.8 ps, DRC 0, LVS MATCH | – |

The abstract, text, tables and figures all read these from the JSON files via placeholders, so regenerating
the JSON and rebuilding keeps the page consistent.

---

## 7. Pitfalls discovered (do not re-learn these)

1. **Model calibration vs VDD sweeps.** `ids()` originally calibrated its constant lazily at the first call; a
   sweep starting at 0.5 V over-calibrated the ring study by ~2×. Fixed: eager calibration at `VDD_NOM`.
   Any new script that sweeps `rm.VDD` is safe now; do not reintroduce lazy calibration.
2. **Headless Chromium viewport offset.** `--window-size` in `--headless=new` includes ~87 px of browser
   chrome; `render_pngs.py` probes the offset once and crops. Also inline `max-width:100%` on SVGs must be
   overridden with `!important`. Both are handled; reuse `render_pngs.py` rather than ad-hoc screenshots.
3. **DRC spacing rule is Euclidean** (closing operation); corner-to-corner gaps count. `NS.S.1` is 16 nm (single
   diffusion break); butted contacts (SDC overlapping CB) are exempt from `SDC.S.GATE`.
4. **LVS naming.** Labels on texttype 2 are ports; texttype 3 are net names (not ports). Hierarchical labels
   from SREFs are ignored except VDD/VSS (virtually connected by name). `flatten()` in gdstk works in place:
   capture `top.labels` before flattening. The top cell is chosen as the one with most references.
   Synthesis internal nets are named `syn_netK` to avoid colliding with RTL vector bits `n[K]` → `n_K`.
5. **Spectre parsing** in `gaa3_lvs.py` joins `\`-continued lines and handles several statements per line.
6. **Router:** metal-2 only, 5 tracks (84, 56, 112, 140, 28), rectangle-spacing checks against routed metal
   and per-cell M2 obstructions (NAND2 has two). Placement trials: chain order → flipped obstructed cell →
   obstructed-last → both. SREF mirroring uses STRANS reflection + 180° (works with gdstk).
7. **SNM extraction**: use the direct largest-square search (`sram6t.snm`); the 45° rotation shortcut gives
   nonsense (>VDD/2) because the rotated curve is not single-valued.
8. **PEX dominant term** is the device-level gate-to-S/D coupling (0.25 aF per nm of W_eff per side); metal
   terms are <10 aF per net. Post-layout: coupling applied via dV_in/dt on the driver, ×2 (Miller) on loads,
   half the net resistance in series. `.lib` pin capacitance already includes gate parasitics; post-route STA
   adds only `cgnd_wire_aF + ccoup_wire_aF` from the PEX JSON.
9. `build_page.py` fails loudly on a missing placeholder — intended.

---

## 8. What the owner must do in the VMware guest (to make the paper camera-ready)

1. Set `CDS_LIC_FILE`, `CDSHOME`, `GAA3_LIB` (see README §1); mount the repo via a shared folder.
2. Stream the four GDSII files into Virtuoso with `layout/gaa3.layermap`; run Pegasus DRC/LVS with the same
   rule names as `verify/gaa3_drc.py`; capture the viewer windows → replace Figs. 16-17.
3. Run the Spectre testbenches (`spectre/*.scs`) with BSIM-CMG; capture ViVA → replace Fig. 9, Figs. 7-8, 12, 14
   data and Tables III, VI, VII, VIII numbers (all placeholders come from `spectre/results*.json`; the simplest
   path is to write the Spectre measurements into those JSON files in the same keys and rebuild).
4. Quantus QRC with `verify/gaa3_qrc.ccl` → replace Fig. 18, Table XI; rerun ADE on `av_extracted` → Fig. 19, Table XII.
5. Genus (`genus/synth.tcl`, `synth_ro.tcl`) and Innovus (`innovus/pnr.tcl`) with the real GAA3 kit → Tables XIII-XIV, Figs. 20-21.
6. Capture Virtuoso schematic windows → replace Fig. 3.
7. Remove the provenance box in Section IV and the "ref." status lines once real captures are in.

---

## 9. Open items / ideas for the next session

* Variability (sheet thickness, work function) and self-heating are explicitly out of scope in the paper; a
  Monte-Carlo SNM / delay section would be the natural next addition (the model is cheap to sample).
* High-Vth flavour for SRAM leakage (the paper notes the SVT calibration makes bitcell leakage high).
* Word-line Elmore delay is pessimistic (Table XII); a strapped/segmented WL model would be more realistic.
* The reference router is single-layer (M2); larger designs would need M3 vertical routing.
* A Word/LaTeX export of the page for journal submission (figures are in `docs/figures/*.png`, 2×).
* Journal target not yet chosen; candidates discussed implicitly: IEEE TED, IEEE JSSC (unlikely for a cell-level
  study), Microelectronics Journal, IEEE Access, Elsevier Integration. Check scope and page limits before export.

---

## 10. Conventions for anyone continuing

* Commit messages end with the Co-Authored-By / Claude-Session lines used throughout the branch.
* Never put model identifiers in files pushed to the repository.
* Keep every number in the page sourced from a JSON file via a placeholder; never type a number into the template.
* When adding a figure, add it to `render_pngs.py` NAMES so a PNG exists for the manuscript export.
* Keep `docs/figures/README.md` and `README.md` tables up to date when adding deliverables.

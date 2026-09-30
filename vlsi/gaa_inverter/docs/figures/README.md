# Rendered figures

| File | Content |
|---|---|
| `schematic_inv.png` / `.svg` | INV_GAA_X1 transistor-level schematic |
| `schematic_nand2.png` / `.svg` | NAND2_GAA_X1 schematic (series NMOS stack, parallel PMOS) |
| `schematic_ro11.png` / `.svg` | RO11_GAA: 11 inverters with loop-closing feedback |
| `schematic_sram6t.png` / `.svg` | SRAM6T_GAA_HD: cross-coupled inverters, PG1/PG2, BL/BLB/WL |
| `virtuoso_{inv,nand2,ro11,sram6t}.png` / `.svg` | The same schematics in the Virtuoso Schematic Editor convention (device/wire/annotation layers, window frame) |
| `viva_{inv_dc,inv_tran,nand2_tran,ro11_tran,sram_butterfly}.png` / `.svg` | Simulation results in the ViVA waveform-viewer convention with markers (reference-model data) |
| `drc_{inv,nand2,ro11,sram6t}.png`, `lvs_{...}.png` / `.svg` | DRC and LVS results in the Pegasus results-viewer convention (from `verify/*.json`) |
| `innovus_{inverter,nand2,ring_osc}.png`, `genus_*.png`, `timing_*.png` | RTL-to-GDSII results in the Innovus / Genus window conventions (from `flow/reports`) |
| `layout_inv.png` | GDSII rendering of `layout/gaa_inverter.gds` (96 x 168 nm) |
| `layout_nand2.png` | GDSII rendering of `layout/gaa_nand2.gds` (144 x 168 nm) |
| `layout_ro11.png` | GDSII rendering of `layout/gaa_ro11.gds` (1056 x 168 nm, flattened) |
| `layout_sram6t.png` | GDSII rendering of `layout/gaa_sram6t.gds` (216 x 96 nm) |

`schematic_*_page.svg` are the theme-token variants embedded in the manuscript page.
Regenerate with `python3 ../gen_schematics.py`, `python3 ../gen_schematics_virtuoso.py`, `python3 ../gen_viva.py` and
`python3 ../render_pngs.py` (2x headless-Chromium screenshots, cropped to the SVG size). Layout colours follow `layout/gen_gaa_inverter_gds.py` STYLE.

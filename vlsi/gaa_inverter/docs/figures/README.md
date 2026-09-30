# Rendered figures

| File | Content |
|---|---|
| `schematic_inv.png` / `.svg` | INV_GAA_X1 transistor-level schematic |
| `schematic_nand2.png` / `.svg` | NAND2_GAA_X1 schematic (series NMOS stack, parallel PMOS) |
| `schematic_ro11.png` / `.svg` | RO11_GAA: 11 inverters with loop-closing feedback |
| `schematic_sram6t.png` / `.svg` | SRAM6T_GAA_HD: cross-coupled inverters, PG1/PG2, BL/BLB/WL |
| `layout_inv.png` | GDSII rendering of `layout/gaa_inverter.gds` (96 x 168 nm) |
| `layout_nand2.png` | GDSII rendering of `layout/gaa_nand2.gds` (144 x 168 nm) |
| `layout_ro11.png` | GDSII rendering of `layout/gaa_ro11.gds` (1056 x 168 nm, flattened) |
| `layout_sram6t.png` | GDSII rendering of `layout/gaa_sram6t.gds` (216 x 96 nm) |

`schematic_*_page.svg` are the theme-token variants embedded in the manuscript page.
Regenerate with `python3 ../gen_schematics.py`; PNGs are 2x screenshots of the SVGs
(headless Chromium). Layout colours follow `layout/gen_gaa_inverter_gds.py` STYLE.

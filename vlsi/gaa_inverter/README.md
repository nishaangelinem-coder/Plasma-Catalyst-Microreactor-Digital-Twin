# GAA Nanosheet Inverter: Cadence RTL-to-GDSII Flow

Design and implementation of a gate-all-around (GAA) nanosheet CMOS inverter
(`INV_GAA_X1`, 3-nm-class generic rules) with a complete Cadence flow:

| Stage | Tool (VMware guest) | Script | Output |
|---|---|---|---|
| Device / cell design | Virtuoso Schematic + Spectre (BSIM-CMG) | `spectre/gaa_inv_tb.scs` | VTC, delay, power |
| Cell layout | Virtuoso Layout XL, Pegasus/PVS DRC-LVS | `layout/gen_gaa_inverter_gds.py`, `layout/streamout_virtuoso.il` | `layout/gaa_inverter.gds` |
| RTL | Xcelium | `rtl/inverter.v`, `rtl/inverter_tb.v` | simulation log |
| Synthesis | Genus | `genus/synth.tcl`, `genus/constraints.sdc` | mapped netlist, SDF |
| Place & route | Innovus | `innovus/pnr.tcl`, `innovus/mmmc.tcl` | DEF, SPEF, **`inverter.gds`** |
| Reference check | Python (no deps) | `spectre/ref_model.py` | `results.json`, SVG figures |

`layout/gaa_inverter.gds` is a valid Calma GDSII stream (1 nm database unit,
library `GAA3_INV_LIB`, cell `INV_GAA_X1`, 32 boundaries, 4 pin texts).
It was written by the dependency-free writer in `gen_gaa_inverter_gds.py`
and read back with `gdstk`.

## 1. VMware Workstation host setup

1. Create a VM: Linux guest (RHEL 8.x / Rocky 8 / CentOS 7.9 are on the Cadence
   support matrix), 4+ vCPU, 16 GB RAM, 120 GB thin-provisioned disk, NAT network.
2. Install VMware Tools / open-vm-tools and enable a shared folder that maps
   this repository into the guest (`/mnt/hgfs/gaa_inverter`).
3. Install the Cadence tools from the IC/DDI/Genus/Innovus/Xcelium installers,
   then set the licence server:
   ```bash
   export CDS_LIC_FILE=5280@license-host      # or LM_LICENSE_FILE
   export CDSHOME=/opt/cadence/IC231
   export GAA3_LIB=/opt/pdk/gaa3               # generic GAA kit: liberty, lef, gds, qrc
   export PATH=$CDSHOME/tools/bin:$CDSHOME/tools/dfII/bin:/opt/cadence/GENUS231/bin:/opt/cadence/INNOVUS231/bin:/opt/cadence/XCELIUM2309/bin:$PATH
   ```
4. Snapshot the VM after installation so a broken flow can be rolled back.

## 2. Cell-level flow (Virtuoso / Spectre)

```bash
cd spectre && spectre gaa_inv_tb.scs +log spectre.log       # BSIM-CMG nanosheet models
python3 ref_model.py                                        # reference metrics for cross-check
GAA_TECH=finfet python3 ref_model.py                        # 5-nm-class FinFET baseline (Table V)
```
In Virtuoso: `File > Import > Stream` the GDS in `layout/` (layer map
`layout/gaa3.layermap`) to obtain the `INV_GAA_X1 layout` cellview, run DRC/LVS,
then `File > Export > Stream` (or `load("streamout_virtuoso.il")`) to regenerate GDSII.

## 3. RTL-to-GDSII flow (Xcelium / Genus / Innovus)

```bash
cd rtl     && xrun -timescale 1ps/1fs inverter.v inverter_tb.v
cd ../genus   && genus   -files synth.tcl -log logs/genus
cd ../innovus && innovus -init  pnr.tcl   -log logs/innovus
# -> innovus/out/inverter.gds (merged with the standard-cell GDS)
```

## 4. Verifying the GDSII

```bash
python3 -c "import gdstk; l=gdstk.read_gds('layout/gaa_inverter.gds'); \
  c=l.cells[0]; print(c.name, len(c.polygons), c.bounding_box())"
klayout layout/gaa_inverter.gds        # optional viewer
```

All numbers in `spectre/results.json` come from the Python reference model,
not from a Spectre run; replace them with the extracted Spectre/Innovus
values after running the flow in the VMware guest.

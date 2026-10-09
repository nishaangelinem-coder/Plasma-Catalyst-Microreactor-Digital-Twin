# Reproducing the design in Cadence Virtuoso / Spectre (VMware workstation flow)

The cloud session that produced this repository has **no access to the user's VMware
machine or to any Cadence installation**; everything here was simulated with ngspice
and an in-house conversion-matrix (PSP-equivalent) solver. The files in this folder
are written so that the same analyses can be run in Virtuoso with a real PDK and the
figures of merit regenerated. Steps:

1. **Copy** `cadence/` and `models/` to the VM (shared folder or `scp`). Start Virtuoso
   from a terminal where the PDK is sourced (`virtuoso &`).
2. **Create the library.** In the CIW: `load("build_schematics.il")`. Edit `pdkLib`
   at the top of the file to the PDK library name (e.g. `tsmcN65`, `gpdk045`,
   `umc65ll`) and the device names (`nch_rf`, `pch_rf`, `nmoscap_rf`, `mimcap`).
   The script creates `circulator_lib` with `mbvd_linbo3`, `res_cell`, `inv_*`,
   `drv_s*`, `vdrv`, `phasegen` and `tb_circulator_core`; wire the nets following
   `circulator_core.scs` / `circulator_full.scs` (or import the netlists directly:
   File -> Import -> Spice, Spectre syntax).
3. **Core S-parameters.** `load("psp_sparams.ocn")` in the CIW, or ADE-L: analyses
   `pss` (fund = fm, harms 40, tstab 400 ns, errpreset conservative) followed by
   `psp` (0.9-1.1 GHz, 201 points, ports PORT1-3, portharmsvec [0 0 0]). Plot
   `dB20(spm(2 1))`, `dB20(spm(1 2))`, `dB20(spm(1 1))`. Sideband conversion:
   repeat psp with `portharmsvec [1 0 0]` / `[-1 0 0]`.
4. **Transistor-level verification.** Use `circulator_full.scs`: run `tran` for the
   waveforms (clock, PH0/120/240, VT0-2, port voltages) and `pss` with the clock as
   fundamental plus `psp` for S-parameters including the real drivers. Compare with
   `results/ngspice_summary.json`.
5. **Linearity / power handling** (not simulated in the cloud): `qpss`/`hb` with a
   two-tone source at port 1, sweep power, extract IIP3 and P1dB.
6. **Monte-Carlo / mismatch**: ADE-XL, vary resonator fs (+/-0.1 %) and varactor
   Cmax (+/-5 %) per cell; the per-channel `Vdc` trim restores isolation.
7. **Layout.** Import `layout/circulator_driver_top.gds` (File -> Import -> Stream;
   map the generic layers listed in `layout/gen_layout.py` to the PDK layers with a
   layer map), then run Calibre/PVS DRC and LVS against the PDK rules. The GDS is a
   floor-plan-level tape-out candidate: device cells should be replaced by PDK
   pcells before sign-off.

Each `.scs` file lists the parameters that come from `results/design_final.json`.

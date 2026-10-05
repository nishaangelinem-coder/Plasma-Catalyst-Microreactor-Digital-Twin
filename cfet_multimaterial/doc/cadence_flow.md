# Cadence Virtuoso / Spectre flow — step-by-step mapping of the 38-step brief

This document maps every step of the circuit-validation brief to the script or
file that performs it. All paths are relative to `cfet_multimaterial/`.

**Where it runs.** Virtuoso is not installed in the authoring environment; the
whole flow is meant to run on the user's Cadence host, typically the
**VMware Linux VM** (`virtuoso`, `spectre`, `ocean` on the PATH). Set
`CFET_ROOT` to the checkout path inside the VM (shared folder or `git clone`)
before starting Virtuoso; every script resolves its paths from it. The scripts
were written against the documented SKILL / OCEAN / Spectre syntax but could
not be executed here, so the first run should be done interactively from the
CIW (see `cadence/README.md`), checking `cfetReportFunctions()` output for the
release-dependent functions.

Legend: **SKILL** = `cadence/skill/*.il` (CIW `load(...)`), **OCEAN** =
`cadence/ocean/*.ocn` (`ocean -nograph -restore file.ocn`, or CIW `load`),
**GUI** = ADE Explorer / Assembler (`cadence/ade/maestro_setup.md`),
**SCS** = hand-written Spectre netlist (`netlists/spectre/`).

| # | Brief step | Performed by | Notes |
|---|---|---|---|
| 1 | Create the working library `CFET_LIB` (no tech file, or attached to a tech lib) | **SKILL** `create_cfet_lib.il` → `cfetCreateLib()` (`ddCreateLib`, optional `techBindTechFile` via `CFET_TECH_LIB`); `cadence/cds.lib.add` | Library path `cadence/CFET_LIB` |
| 2 | Import the nine Verilog-A models as `veriloga` cellviews | **SKILL** `cfetImportVerilogA(cell)` for `gaa_n gaa_p sige_p mos2_n wse2_p cnt_n cnt_p gan_n gan_p` | `ddGetObj(... "veriloga" "veriloga.va" t)` + file copy; `vaCreateCellView` when available; parser via `ahdlCompile`/editor-save |
| 3 | CDF with the UCM-CFET parameter list `W L NNS ... ALPHA` | **SKILL** `cfetCreateCDF(cell)` (`cdfCreateBaseCellCDF`, `cdfCreateParam`, `simInfo->spectre termOrder (d g s b)`) | Empty CDF defaults → module defaults; schematics set all values |
| 4 | Symbols from the Verilog-A view, terminal order d g s b | **SKILL** `cfetCreateSymbol(cell)` (`schViaSymbolGen` / `ahdlGenerateSymbol` if callable, else `cfetDrawSymbol` with `schCreateSymbolPin`) | GUI path: *File → New → Cellview → From Cellview* |
| 5 | Device testbench `tb_<device>` with `vdc` VGS, `vdc` VDS, `gnd` | **SKILL** `build_schematics.il` → `cfetBuildDeviceTB(cell)` | Sources `VG`, `VD`; p-type uses `-VGS`, `-VDS`; **SCS** `tb_<device>_idvg.scs` |
| 6 | ID-VG: VGS 0..0.8 V step 2 mV at VDS = 0.05 and 0.6 V, save I(VDS) | **OCEAN** `idvg.ocn`; **SCS** `tb_<device>_idvg.scs` (`idvgLin`, `idvgSat`) | GaN uses 0..1.5 V and VDS 1.2 V; CSV `results/idvg_<device>.csv` |
| 7 | ID-VD: VDS 0..0.8 V for VGS = 0.2 .. 0.7 V | **OCEAN** `idvd.ocn`; **SCS** `idvd sweep` block | CSV `results/idvd_<device>.csv` |
| 8 | Figures of merit: Ion, Ioff, SS, DIBL, gm, gds | **OCEAN** `extract_fom.ocn` (`value`, `deriv`, `cross`, `clip`, `ymin`) | `results/device_fom.csv` |
| 9 | Calibration / MAPE against the reference data | `sim/ucm.py` + `sim/platforms.py` (Python, outside Cadence) using the CSVs of steps 6–8 | Cadence side only exports the curves; the Verilog-A parameters come from the calibrated `sim/platforms.py` |
| 10 | Nominal parameter sets per material in SI units | `cadence/skill/build_schematics.il` (`cfetDeviceNominal`, `cfetPlatforms`), `cadence/ocean/cfet_common.ocn`, `cadence/ade/design_variables.csv`, **SCS** `parameters` lines | Identical numbers in all four places |
| 11 | Inverter cells `inv_cfet_<plat>` with CFET parasitics (Cstack, Cout, Rlocal_n, Rlocal_p) | **SKILL** `cfetBuildInverter(plat)`; **SCS** `inv_cfet_<plat>.scs` | Values via cell CDF `CSTACK COUT RLOCAL` (`pPar`); mid-range defaults Si/SiGe 0.05f/0.3f/10, TMD/CNT 0.03f/0.3f/50, GaN 0.1f/1f/20 |
| 12 | Inverter symbols (pins in out vdd vss) | **SKILL** `cfetBoxSymbol(cell ...)` | Deterministic box symbol |
| 13 | Inverter testbench `tb_inv_cfet_<plat>` (vdc VDD, vpulse VIN, cap CLOAD) | **SKILL** `cfetBuildInverterTB(plat)`; **SCS** `tb_inv_cfet_<plat>.scs` | VIN: V1=0 V2=VDD td=100p tr=5p tf=5p pw=500p per=1n |
| 14 | VTC: VM, gain, NML, NMH, static IDD | **OCEAN** `vtc.ocn` (dc sweep of `/VIN dc`, `cross`, `deriv`); **SCS** `vtc dc dev=VIN param=dc` | `results/vtc_<plat>.csv`, `results/inverter_vtc.csv` |
| 15 | Transient delay tpHL / tpLH at 50 % crossings | **OCEAN** `inv_tran.ocn` (`delay(?wf1 ... ?wf2 ...)`) | `results/inverter_tran.csv` |
| 16 | Switching energy Eswitch = ∫VDD·I(VDD) dt | **OCEAN** `inv_tran.ocn` (`integ(pvdd t0 t1)`) | One full period from the first input edge |
| 17 | Ring oscillators ro5 / ro7 / ro9 per platform (odd rings, nodes n1..nN, closed) | **SKILL** `cfetBuildRing(plat n)` for `cfetRingStages = (5 7 9)`; **SCS** `ro5_cfet_<plat>.scs`, `roN_cfet_template.scs`, `roN_expand.awk` | Pin `n1` of the ring = observation node `out` |
| 18 | RO symbols | **SKILL** `cfetBoxSymbol` (pins n1, vdd, vss) | |
| 19 | RO testbench `tb_ro5_cfet_<plat>` (vdc VDD, ic node) | **SKILL** `cfetBuildRingTB(plat n)` (also tb_ro7/tb_ro9) | `ic` lives in ADE/OCEAN, not in the schematic |
| 20 | Transient settings table (stop, maxstep per platform) | `cfet_common.ocn` (`roStop`, `roMaxstep`), `maestro_setup.md` §3, **SCS** `tran1` lines | Si/SiGe/CNT 5n/1p, TMD 50n/10p, GaN 20n/5p, `errpreset=conservative` |
| 21 | RO start-up by initial condition | **OCEAN** `ro_tran.ocn` → `ic("/out" 0.0)`; **SCS** `ic n1=0`; GUI *Convergence Aids → Initial Condition* | default |
| 22 | RO start-up by 1 % mismatch (alternative) | **SKILL** `CFET_RO_MISMATCH_STARTUP = t` before `cfetBuildAll()` (stage I1 `VTHN = 1.01*VTHN`); **SCS** `parameters MISMATCH=0.01`; **OCEAN** `CFET_RO_STARTUP = "mismatch"` | |
| 23 | fRO from two successive rising crossings at VDD/2 (cycles 10 → 11) | **OCEAN** `cfet_common.ocn` → `cfetRoFomFromWaves` (`cross(vout vdd/2 10/11 "rising")`), used by `ro_tran.ocn` | |
| 24 | tpd = 1/(2 N fRO) | same | N from the testbench name |
| 25 | Pavg = average(VDD·I(VDD)) post start-up | same (`average(clip(pvdd t10 tend))`) | |
| 26 | Ecycle = Pavg/fRO, PDP = Pavg·tpd | same | `results/ro_fom.csv`, waveforms `results/ro<N>_<plat>.csv` |
| 27 | Supply sweep (Si/SiGe/CNT 0.4..0.8 step 0.05, TMD 0.3..0.6, GaN 0.8..1.5 step 0.1) | **OCEAN** `vdd_sweep.ocn` (`paramAnalysis("VDD")`, `famValue`); GUI `maestro_setup.md` §5.3; **SCS** commented `vddsw sweep` | `results/vdd_sweep.csv` |
| 28 | ADE Assembler sweeps / tests set-up | **GUI** `cadence/ade/maestro_setup.md` §5; variables `cadence/ade/design_variables.csv` | |
| 29 | Corners (temperature × VDD per platform) | `cadence/ade/corners.csv`; GUI §5.4 | |
| 30 | Temperature sweep −40, 27, 85, 125 °C (+150, 200 °C for GaN) | **OCEAN** `temp_sweep.ocn` (`temp(T)`); **SCS** commented `tsw sweep param=TEMP` | `results/temp_sweep.csv` |
| 31 | Si/SiGe sensitivity: NNSn, NNSp 2..5, MUP ratio 1..2 | **OCEAN** `sensitivity_si.ocn` | `results/sensitivity_si.csv` |
| 32 | TMD sensitivity: RCN, RCP 0.1..2 kΩ·µm, DIT 1e11..1e13 cm⁻²eV⁻¹ | **OCEAN** `sensitivity_tmd.ocn` (RC → Ω·m, DIT → m⁻²eV⁻¹) | `results/sensitivity_tmd.csv` |
| 33 | CNT sensitivity: DCNT low/nom/high, FMET 0..2 %, RC 50..1000 Ω·µm | **OCEAN** `sensitivity_cnt.ocn` | `results/sensitivity_cnt.csv` |
| 34 | GaN sensitivity: TEMP 300..500 K, RTH, VTH ±5..15 % | **OCEAN** `sensitivity_gan.ocn` | `results/sensitivity_gan.csv` |
| 35 | Statistical model (process + mismatch σ per platform) | `cadence/ade/mc_statistics.scs` (`statistics { process {...} mismatch {...} }`, sections `si sige tmd cnt gan`) | Si VTH0 20 mV / WNS 1 nm / RSW 10 %; SiGe + MU0 10 %; TMD RC 30 %, VTH0 50 mV, MU0 20 %, DIT 0.3 dec; CNT DCNT 15 %, FMET unif 0–2 %, RC 30 %; GaN VTH0 50 mV, MU0 10 %, RTH 20 % |
| 36 | Monte Carlo 100 (debug) / 1000 (publication), saving fRO Pavg Ecycle PDP VM gain tpd | **OCEAN** `montecarlo.ocn` (Assembler `ocnxl*` API, `CFET_MC_POINTS`); GUI §6; **SCS** commented `mc1 montecarlo` block | `results/mc_<plat>_N<N>.csv`, summary txt |
| 37 | Yield: Yf = N(fRO ≥ ftarget)/N and functional yield (NML > 0.1 VDD, NMH > 0.1 VDD, Av > 10) | **OCEAN** `montecarlo.ocn` (`?specType/?specLimit` on the expressions + `cfetMcYieldFromCsv`) | `results/mc_yield.csv`; `ftarget` table `cfetFtarget` to be filled from `results/ro_fom.csv` |
| 38 | Conceptual CFET layout (stacked n/p, local vias) | Not scripted: attach a tech library (`CFET_TECH_LIB` in `create_cfet_lib.il`), draw in Virtuoso Layout XL from the inverter schematic; `layout/` holds the figures | Parasitic values Cstack/Cout/Rlocal of step 11 are the link between layout and circuit |

## Execution order

```text
cadence/cds.lib.add                     -> cds.lib
create_cfet_lib.il   cfetCreateAll()     steps 1-4
build_schematics.il  cfetBuildAll()      steps 5, 11-13, 17-19
idvg.ocn / idvd.ocn / extract_fom.ocn    steps 6-8      (-> sim/ for step 9)
vtc.ocn / inv_tran.ocn                   steps 14-16
ro_tran.ocn                              steps 20-26    (CFET_RO_STAGES = list(5 7 9))
vdd_sweep.ocn / temp_sweep.ocn           steps 27, 30
sensitivity_*.ocn                        steps 31-34
montecarlo.ocn                           steps 35-37    (fill cfetFtarget first)
maestro_setup.md                         interactive equivalents, steps 27-29, 36
```

## Spectre-only path (no Virtuoso licence)

`netlists/spectre/` reproduces every testbench; run from that directory so the
relative `ahdl_include "../../veriloga/<cell>.va"` lines resolve:

```bash
cd netlists/spectre
for f in tb_*_idvg.scs tb_inv_cfet_*.scs ro5_cfet_*.scs; do
  spectre $f -format psfascii -raw ../../results/spectre/${f%.scs}
done
awk -v N=7 -v P=si -f roN_expand.awk > ro7_cfet_si.scs     # 7- and 9-stage rings
```

The psfascii results are post-processed with the same formulas as the OCEAN
scripts (steps 23–26) in Python (`sim/`), which also produces the paper figures.

## Known caveats (checked at run time by the scripts)

* `vaCreateCellView`, `ahdlCompile`, `schViaSymbolGen`, `ahdlGenerateSymbol`
  are release dependent; `cfetReportFunctions()` prints which exist. Without
  them: open each `veriloga` view once in the text editor and save (CDF), then
  the manual symbol builder is used automatically.
* `ocnxlExportOutputView` (CSV export of Monte Carlo results) is guarded by
  `isCallable`; if absent, export from the Assembler Results tab and run
  `cfetMcYieldFromCsv()` on that file.
* Design-variable units: all SI (RC in Ω·m, DIT in m⁻²eV⁻¹, DCNT in m⁻¹). The
  brief's kΩ·µm and cm⁻²eV⁻¹ ranges are converted inside `sensitivity_*.ocn`.
* Temperature is the ADE/Spectre `temp` option; the design variable `TEMP` is
  only bookkeeping.

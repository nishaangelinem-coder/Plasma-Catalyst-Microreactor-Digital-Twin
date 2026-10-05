# ADE Explorer / ADE Assembler (Maestro) setup for the CFET validation flow

This is the GUI counterpart of the OCEAN scripts in `../ocean/`. Everything
below assumes `CFET_LIB` exists and `build_schematics.il` has been run (see
`../README.md`). Menu names refer to IC6.1.8 / IC23.1; Explorer is the
single-test view, Assembler adds the tests/corners/sweeps tables.

## 1. Open a testbench in ADE Explorer

1. Library Manager -> `CFET_LIB` -> `tb_ro5_cfet_si` -> `schematic` -> open.
2. Schematic window: **Launch -> ADE Explorer** (creates the `maestro` view
   when you save; save it as `CFET_LIB/tb_ro5_cfet_si/maestro`).
3. **Setup -> Simulator/Directory/Host**: Simulator `spectre`, project directory
   `$CFET_ROOT/cadence/work/simulation`.
4. **Setup -> Model Libraries**: nothing is needed for nominal runs; the
   `veriloga` views of `CFET_LIB` are netlisted automatically (check the
   netlist: `Simulation -> Netlist -> Display` must contain
   `ahdl_include ".../gaa_n/veriloga/veriloga.va"` lines). For Monte Carlo add
   `$CFET_ROOT/cadence/ade/mc_statistics.scs` with **Section** = the platform
   name (`si`, `sige`, `tmd`, `cnt`, `gan`).
5. **Setup -> Environment**: `Switch View List` = `spectre cmos_sch cmos.sch
   schematic veriloga ahdl symbol`, `Stop View List` = `spectre veriloga`.
   (This makes the netlister descend into the schematics and stop at the
   Verilog-A views.)

## 2. Global design variables

In the **Design Variables** pane click *Copy From Cellview* (the schematics
reference every variable as an instance parameter) and fill the values from
`design_variables.csv` (column of the platform). Nominal values:

| Variable | Si | SiGe | TMD | CNT | GaN | Note |
|---|---|---|---|---|---|---|
| VDD | 0.7 | 0.7 | 0.5 | 0.6 | 1.2 | V |
| VGS, VDS | 0, 0.05 | 0, 0.05 | 0, 0.05 | 0, 0.05 | 0, 0.05 | device TBs (swept) |
| CLOAD | 1f | 1f | 1f | 1f | 2f | inverter TB |
| CSTACK / COUT / RLOCAL | 0.05f / 0.3f / 10 | 0.05f / 0.3f / 10 | 0.03f / 0.3f / 50 | 0.03f / 0.3f / 50 | 0.1f / 1f / 20 | CFET parasitics |
| Wn / Wp | (NNS) | (NNS) | 100n / 200n | 100n / 100n | 1u / 4u | m |
| Lg | 16n | 16n | 20n | 15n | 100n | m |
| NNSn / NNSp | 3 / 3 | 3 / 3 | - | - | - | nanosheets |
| WNS / RSW | 20n / 1e-4 | 20n / 1e-4 | - | - | - | MC variables |
| VTHN / VTHP | 0.25 / 0.25 | 0.25 / 0.22 | 0.20 / 0.25 | 0.20 / 0.22 | 0.30 / 0.50 | V |
| MUN / MUP | 0.030 / 0.015 | 0.030 / 0.025 | 5e-3 / 4e-3 | - | 0.15 / 2e-3 | m²/Vs |
| RCN / RCP | - | - | 5e-4 / 8e-4 | 1e-4 / 1e-4 | - | Ω·m |
| DIT | - | - | 1e16 | - | - | m⁻²eV⁻¹ (=1e12 cm⁻²eV⁻¹) |
| DCNT / FMET | - | - | - | 250e6 / 0.01 | - | m⁻¹ / - |
| RTH / CTH | - | - | - | - | 2e5 / 1e-12 | K/W, J/K |
| TEMP | 27 | 27 | 27 | 27 | 27 | °C, use *Setup -> Temperature* |

Variables marked "-" can be set to 0; they are not referenced by that
platform's schematic. `TEMP` is kept as a variable for bookkeeping; the
simulation temperature itself is **Setup -> Temperature** (Explorer) or the
`temperature` column of the Corners table (Assembler).

## 3. Analyses per testbench

| Testbench | Analysis (Analyses -> Choose) | Settings |
|---|---|---|
| `tb_<device>` ID-VG | dc, Design Variable `VGS` | 0 .. 0.8 (GaN 1.5), linear, step 0.002; run at VDS = 0.05 and VDS = 0.6 (GaN 1.2) |
| `tb_<device>` ID-VD | dc, Design Variable `VDS` | 0 .. 0.8 (GaN 1.5), step 0.005; parametric on VGS 0.2 .. 0.7 step 0.1 |
| `tb_inv_cfet_<plat>` VTC | dc, Component Parameter `/VIN` `dc` | 0 .. VDD, step 0.001 |
| `tb_inv_cfet_<plat>` delay | tran | stop 2n (TMD/GaN 5n), maxstep = RO maxstep, errpreset conservative |
| `tb_ro5_cfet_<plat>` | tran | stop/maxstep from the table below, errpreset conservative |

RO transient settings (brief "transient settings table"):

| Platform | stop | maxstep | expected fRO order | start-up |
|---|---|---|---|---|
| Si | 5 ns | 1 ps | ~10 GHz | ic /out = 0 |
| SiGe | 5 ns | 1 ps | ~10 GHz | ic /out = 0 |
| TMD | 50 ns | 10 ps | ~1 GHz | ic /out = 0 |
| CNT | 5 ns | 1 ps | ~10 GHz | ic /out = 0 |
| GaN | 20 ns | 5 ps | ~3 GHz | ic /out = 0 |

Start-up: **Simulation -> Convergence Aids -> Initial Condition**, click the
`out` net, value 0. Alternative (brief step 23): rebuild the ring with
`CFET_RO_MISMATCH_STARTUP = t` so stage I1 has `VTHN = 1.01*VTHN`.

**Outputs -> To Be Saved -> Select On Schematic**: `out` (voltage) and the
`PLUS` terminal of `VDD` (current). For the device TBs select the `PLUS`
terminal of `VD`.

## 4. Output expressions (Outputs -> Setup, type Expression)

Copy from the OCEAN scripts; `VAR("VDD")` reads a design variable.

| Name | Expression |
|---|---|
| fRO | `1/(cross(VT("/out") VAR("VDD")/2 11 "rising") - cross(VT("/out") VAR("VDD")/2 10 "rising"))` |
| tpd | `1/(2*5*fRO)` (replace 5 by N) |
| Pavg | `average(clip(VAR("VDD")*(-IT("/VDD/PLUS")) cross(VT("/out") VAR("VDD")/2 10 "rising") xmax(VT("/out"))))` |
| Ecycle | `Pavg/fRO` |
| PDP | `Pavg*tpd` |
| VM | `cross(VS("/out") - VS("/in") 0 1 "falling")` |
| gain | `ymax(abs(deriv(VS("/out"))))` |
| NML | `cross(deriv(VS("/out")) (0-1) 1 "falling") - value(VS("/out") VAR("VDD"))` |
| NMH | `value(VS("/out") 0) - cross(deriv(VS("/out")) (0-1) 1 "rising")` |
| tpHL | `delay(?wf1 VT("/in") ?value1 VAR("VDD")/2 ?edge1 "rising" ?nth1 1 ?wf2 VT("/out") ?value2 VAR("VDD")/2 ?edge2 "falling" ?nth2 1)` |
| tpLH | `delay(?wf1 VT("/in") ?value1 VAR("VDD")/2 ?edge1 "falling" ?nth1 1 ?wf2 VT("/out") ?value2 VAR("VDD")/2 ?edge2 "rising" ?nth2 1)` |
| Eswitch | `integ(VAR("VDD")*(-IT("/VDD/PLUS")) 100p 1.1n)` |
| Ion | `value(-IS("/VD/PLUS") VAR("VDD"))` (n-type; drop the minus sign for p-type TBs) |
| Ioff | `value(-IS("/VD/PLUS") 0)` |
| SS | `1000*ymin(clip(1/deriv(log10(abs(-IS("/VD/PLUS")))) 0 0.15))` |

(`VT`/`IT` = transient, `VS`/`IS` = dc sweep results in the ADE calculator.)

## 5. Convert to ADE Assembler (sweeps, corners)

1. In Explorer: **Launch -> ADE Assembler** (the maestro view is reused); the
   current setup becomes test `tb_ro5_cfet_si:1`.
2. **Add tests** with *Create -> Test* for the other platforms' testbenches
   (one test per `tb_ro5_cfet_<plat>` and `tb_inv_cfet_<plat>`); each test has
   its own design-variable values (Section 2) and analyses (Section 3).
3. **Global sweep of VDD** (brief "Assembler sweeps"): in the Data View,
   right-click the variable `VDD` -> *Add Sweep*: From/To/Step per platform
   table: Si/SiGe/CNT 0.4..0.8 step 0.05, TMD 0.3..0.6 step 0.05, GaN 0.8..1.5
   step 0.1. Because the ranges differ, either give each test its own local
   `VDD` variable or use the Corners table with one VDD column.
4. **Corners** (`corners.csv`): **Setup -> Corners** (Corners Setup form):
   *Add Corner* per row; columns `temperature` and the design variable `VDD`;
   `Model Files` column points to `mc_statistics.scs` only for the `mc` rows.
   You can import the CSV with *File -> Import* in the Corners form (the format
   is `corner,temperature,VDD`; strip the other columns first).
5. **Temperature sweep**: add corners with temperature -40, 27, 85, 125 (GaN
   also 150, 200); the OCEAN equivalent is `temp_sweep.ocn`.
6. **Material-specific sensitivity**: *Add Sweep* on the respective variable:
   Si/SiGe `NNSn`, `NNSp` 2..5 step 1, `MUP` 0.015..0.03 (ratio 1..2); TMD
   `RCN`,`RCP` 1e-4..2e-3, `DIT` 1e15..1e17 (log); CNT `DCNT` 125e6/250e6/500e6,
   `FMET` 0..0.02 step 0.005, `RCN`=`RCP` 5e-5..1e-3; GaN temperature
   27..227 (300..500 K), `RTH` 1e5..8e5, `VTHN`/`VTHP` +-5/10/15 %.
7. **Run -> Sweeps and Corners**; results appear in the Results tab per
   corner/sweep point. Export: right-click the results table -> *Export* CSV
   into `$CFET_ROOT/results/`.

## 6. Monte Carlo (Assembler)

1. **Setup -> Model Libraries** of every test: add `mc_statistics.scs` with the
   platform section (process + mismatch blocks).
2. Run mode drop-down: **Monte Carlo Sampling**; click the gear icon:
   * Number of Points: `100` (debug) / `1000` (publication)
   * Sampling Method: `Latin Hypercube` (or `Random` to compare); Seed `12345`
   * Statistical Variation: `Process and Mismatch`
   * Save Data: `Monte Carlo (Yield)` plus *Save Process Data* and
     *Save Mismatch Data*; `Dump Parameter Mode` yes
   * Run Nominal: on
3. Outputs: expressions `fRO Pavg Ecycle PDP VM gain tpd NML NMH` (Section 4)
   with specs:
   * `fRO` **>=** `ftarget` (0.8 x nominal fRO of the platform)
   * `gain` **>** 10, `NML` **>** `0.1*VAR("VDD")`, `NMH` **>** `0.1*VAR("VDD")`
4. Run. The Results tab shows per-expression histograms, mean/sigma and the
   **Yield** column (= fraction of samples passing all specs). Yf is the yield
   with only the `fRO` spec enabled; the functional yield uses the three VTC
   specs. *Results -> Print -> Monte Carlo Summary* writes the text summary;
   `montecarlo.ocn` reproduces the same run in batch and recomputes both yields
   from the exported CSV.

## 7. Where results go

* OCEAN scripts write CSV files in `$CFET_ROOT/results/` (`idvg_<dev>.csv`,
  `device_fom.csv`, `vtc_<plat>.csv`, `inverter_vtc.csv`, `inv_tran_<plat>.csv`,
  `inverter_tran.csv`, `ro5_<plat>.csv`, `ro_fom.csv`, `vdd_sweep.csv`,
  `temp_sweep.csv`, `sensitivity_<plat>.csv`, `mc_<plat>_N<N>.csv`,
  `mc_yield.csv`).
* ADE Assembler results stay in `$CFET_ROOT/cadence/work/psf/`; export tables
  with *Export -> CSV* when they are needed for the paper figures.

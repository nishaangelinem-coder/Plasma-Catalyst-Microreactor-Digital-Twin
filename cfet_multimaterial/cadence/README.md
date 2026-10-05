# Cadence Virtuoso / Spectre flow for the multi-material CFET compact model

This directory holds everything needed to reproduce the circuit-validation
part of the paper inside Cadence Virtuoso (IC6.1.8 / IC23.1, Spectre 21+).
Virtuoso is **not** installed in the authoring environment; the scripts were
written against the documented SKILL / OCEAN / Spectre syntax and must be run
in the user's Virtuoso machine (typically the VMware Linux VM). Every script is
heavily commented and checks for optional functions at run time.

```
cadence/
  cds.lib.add                  library definition lines to append to cds.lib
  README.md                    this file
  skill/create_cfet_lib.il     create CFET_LIB, Verilog-A cellviews, CDF, symbols
  skill/build_schematics.il    inverter / RO / testbench schematics + symbols
  ocean/cfet_common.ocn        platform table + helpers (loaded by every .ocn)
  ocean/idvg.ocn               ID-VG at VDS = 0.05 and 0.6 V, CSV export
  ocean/idvd.ocn               ID-VD family VGS = 0.2 .. 0.7 V
  ocean/extract_fom.ocn        Ion, Ioff, SS, DIBL, gm, gds
  ocean/vtc.ocn                VM, gain, NML/NMH, static IDD
  ocean/inv_tran.ocn           tpHL / tpLH / Eswitch
  ocean/ro_tran.ocn            fRO, tpd, Pavg, Ecycle, PDP
  ocean/vdd_sweep.ocn          paramAnalysis on VDD (platform table)
  ocean/temp_sweep.ocn         temperature sweep (-40 .. 125 / 200 C)
  ocean/sensitivity_si.ocn     Si and SiGe sensitivities (NNSn, NNSp, MUP)
  ocean/sensitivity_tmd.ocn    RCN, RCP, DIT
  ocean/sensitivity_cnt.ocn    DCNT, FMET, RC
  ocean/sensitivity_gan.ocn    TEMP, RTH, VTH
  ocean/montecarlo.ocn         Monte Carlo (Assembler ocnxl API) + yield
  ade/maestro_setup.md         ADE Explorer / Assembler GUI walkthrough
  ade/design_variables.csv     global design variables (nominal values, units)
  ade/corners.csv              temperature / VDD corners per platform
  ade/mc_statistics.scs        Spectre statistics blocks per platform
```

The hand-written Spectre netlists that mirror every testbench are in
`../netlists/spectre/` (`tb_<device>_idvg.scs`, `inv_cfet_<plat>.scs`,
`tb_inv_cfet_<plat>.scs`, `ro5_cfet_<plat>.scs`, plus `roN_cfet_template.scs`
and `roN_expand.awk` for the 7- and 9-stage rings), and the step-by-step mapping of the 38-step brief to
these files is in `../doc/cadence_flow.md`.

## 1. Prerequisites

* Cadence Virtuoso (IC6.1.7 or newer; ADE Explorer/Assembler = "Maestro") and
  Spectre (MMSIM/Spectre 19 or newer) on the PATH (`virtuoso`, `spectre`).
* The nine Verilog-A files in `../veriloga/<cell>.va` (one module per file,
  module name == cell name == file basename, terminals `d g s b`).
* `analogLib` and `basic` reference libraries (shipped with Virtuoso).

## 2. Setup steps

1. Export the checkout path and go to a scratch working directory:

   ```bash
   export CFET_ROOT=/home/$USER/Plasma-Catalyst-Microreactor-Digital-Twin/cfet_multimaterial
   mkdir -p $CFET_ROOT/cadence/work && cd $CFET_ROOT/cadence/work
   ```

2. Create `cds.lib` (if you do not have one) and append the library
   definitions (edit `$CDSHOME` / `$CFET_ROOT` to literal paths if your
   Virtuoso does not see those variables):

   ```bash
   sed "s#\$CFET_ROOT#$CFET_ROOT#g; s#\$CDSHOME#$CDSHOME#g" ../cds.lib.add >> cds.lib
   ```

3. Start Virtuoso: `virtuoso &`.

4. In the CIW (Command Interpreter Window) load the SKILL scripts:

   ```skill
   load(strcat(getShellEnvVar("CFET_ROOT") "/cadence/skill/create_cfet_lib.il"))
   cfetCreateAll()            ; library + 9 veriloga cellviews + CDF + symbols
   load(strcat(getShellEnvVar("CFET_ROOT") "/cadence/skill/build_schematics.il"))
   cfetBuildAll()             ; inverters, ROs, testbenches, symbols, schCheck
   ```

   `cfetCreateAll()` prints which optional Cadence functions
   (`vaCreateCellView`, `ahdlGenerateSymbol`, `schViaSymbolGen`, ...) exist in
   your release and falls back to the documented manual symbol builder when
   they are missing. Open one of the `veriloga` views in the text editor and
   save it once (`File -> Save`) if the CDF parameters do not show up in the
   instance property form: the Virtuoso Verilog-A parser regenerates the CDF
   on save.

5. Run an OCEAN script from the CIW or from a shell:

   ```skill
   load(strcat(getShellEnvVar("CFET_ROOT") "/cadence/ocean/idvg.ocn"))
   ```

   ```bash
   ocean -nograph -restore $CFET_ROOT/cadence/ocean/ro_tran.ocn
   ```

   Every script reads `CFET_PLATFORM` / `CFET_DEVICE` (SKILL variables or the
   shell variables of the same name) and defaults to all platforms / all
   devices. Results are written as CSV into `$CFET_ROOT/results/`.

6. Interactive work (sweeps, corners, Monte Carlo) in ADE Assembler follows
   `ade/maestro_setup.md`; the design-variable table and the corner table can
   be imported from `ade/design_variables.csv` and `ade/corners.csv`.

## 3. Running the hand-written Spectre netlists without Virtuoso

```bash
cd $CFET_ROOT/netlists/spectre
spectre tb_gaa_n_idvg.scs -format psfascii -raw ../../results/spectre/tb_gaa_n_idvg
spectre tb_ro5_cfet_si.scs -format psfascii -raw ../../results/spectre/tb_ro5_cfet_si
```

The netlists `ahdl_include` the Verilog-A sources relative to their own
directory, so run `spectre` from `netlists/spectre/` (or pass `-I`).

## 4. Naming conventions

| Object | Name |
|---|---|
| Device cells | `gaa_n gaa_p sige_p mos2_n wse2_p cnt_n cnt_p gan_n gan_p` (views `veriloga`, `symbol`) |
| Inverter cells | `inv_cfet_si inv_cfet_sige inv_cfet_tmd inv_cfet_cnt inv_cfet_gan` |
| Ring oscillators | `ro5_cfet_<plat> ro7_cfet_<plat> ro9_cfet_<plat>` |
| Testbenches | `tb_<device>`, `tb_inv_cfet_<plat>`, `tb_ro5_cfet_<plat>` (also `tb_ro7_...`, `tb_ro9_...`) |
| Design variables | `VDD VGS VDS CLOAD CSTACK COUT RLOCAL Wn Wp Lg NNSn NNSp VTHN VTHP MUN MUP RCN RCP RTH CTH TEMP DIT DCNT FMET RC` |

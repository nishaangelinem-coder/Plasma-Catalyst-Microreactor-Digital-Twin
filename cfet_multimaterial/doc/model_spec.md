# UCM-CFET: Unified Compact Model for Multi-Material CFET Devices — Specification

All nine device models (`gaa_n`, `gaa_p`, `sige_p`, `mos2_n`, `wse2_p`, `cnt_n`, `cnt_p`,
`gan_n`, `gan_p`) share one physics core and add material-specific blocks. The identical
equation set is implemented three times from one parameter source of truth
(`sim/platforms.py`):

1. **Verilog-A** (`veriloga/*.va`) – for Cadence Spectre / ADE Explorer / Assembler.
2. **ngspice behavioural sub-circuits** (`netlists/ngspice/*.lib`) – open-source circuit-level validation.
3. **NumPy reference implementation** (`sim/ucm.py`) – DC calibration, MAPE, fast sweeps.

Terminals: `d g s b` (body tied to source in every circuit, kept for Cadence symbol
compatibility). Internal nodes `di`, `si` (series resistance), `tj` (GaN thermal node).

## Core (n-type convention; p-type uses V_gs → V_sg, V_ds → V_sd and I_d → −I_d)

| Symbol | Equation |
|---|---|
| Thermal voltage | V_T = k_B T_dev / q |
| Temperature | T_dev = T_amb (+ ΔT_sh for GaN) ; μ_T = MU0 (T_dev/TNOM)^−MUEXP ; V_TH,T = VTH0 + KVTH (T_dev − TNOM) |
| Effective oxide cap. | C_ox,eff = COX·CQ/(COX+CQ) (CQ → ∞ for Si/SiGe/GaN) |
| Ideality | n = N0 · (1 + q·DIT / COX) |
| DIBL | V_TH,eff = V_TH,T − ETA · sqrt(V_ds² + δ²) |
| Smooth overdrive (EKV-type) | V_ov = 2 n V_T ln(1 + exp((V_gs − V_TH,eff)/(2 n V_T))) — V_ov² ∝ exp((V_gs−V_TH)/(nV_T)) in weak inversion so SS = n V_T ln10; V_ov → V_gs − V_TH in strong inversion |
| Velocity-sat. voltage | V_sat,v = VSAT · L / μ_T |
| Saturation voltage | V_dsat = V_ov / (1 + V_ov / V_sat,v) |
| Transconductance factor | β = μ_T C_ox,eff W / L |
| Drain current (DD) | I_D = β V_ov² / (2 (1 + V_ov/V_sat,v)) · tanh(2 V_ds / V_dsat) · (1 + LAMBDA·sqrt(V_ds²+δ²)) |
| Series resistance | V(d,di) = I·RDW/W ; V(s,si) = I·RSW/W |
| Charges | Q_gs = ½ W L C_ox,eff V_ov(V_gs) + CGSO·W·V_gs ; Q_gd = ½ W L C_ox,eff V_ov(V_gd) + CGDO·W·V_gd (V_ov evaluated without DIBL so each charge depends on its own branch voltage only) ; I = dQ/dt |

The `tanh(2V_ds/V_dsat)` interpolation gives exactly g_ds0 = β V_ov in the linear region and
I_D,sat = β V_ov²/(2(1+V_ov/V_sat,v)) in saturation (square law for long channel,
C_ox W v_sat V_ov/2 for the fully velocity-saturated limit). It is odd in V_ds and infinitely
differentiable, which is what Spectre's Newton iterations need.

## Material blocks

| Platform | Transport block | Extra parameters |
|---|---|---|
| Si GAA n/p, SiGe p | drift-diffusion + velocity saturation (core) | NNS, WNS, TNS → W = NNS·2·(WNS+TNS) |
| MoS₂ n / WSe₂ p | core + quantum capacitance CQ + trap-limited ideality (DIT) + contact resistance RC dominated RS/RD | CQ, DIT, RC |
| CNT n/p | Landauer quasi-ballistic: I_tube = G0·TTR·V_T·[F(η_s) − F(η_s − V_ds/V_T)], F(x)=ln(1+eˣ), η_s = α(V_gs−V_TH)/V_T ; N_tube = DCNT·W·(1−FMET) ; metallic shunt G_met = FMET·DCNT·W·G0·TTR | DCNT, FMET, TTR, ALPHA, G0 = 4q²/h |
| GaN n/p | core + self-heating: thermal node, P = I_D V_ds, I(tj) = V(tj)/RTH + CTH dV(tj)/dt, T_dev = T_amb + V(tj) | RTH, CTH |

## Parameter names (identical in Verilog-A, ngspice and Python)

`W L NNS WNS TNS VTH0 N0 ETA MU0 COX VSAT LAMBDA RSW RDW CGSO CGDO TNOM MUEXP KVTH CQ DIT RC RTH CTH DCNT FMET TTR ALPHA`

SI units throughout (m, V, A, F, Ω·m for RSW/RDW/RC, F/m for CGSO/CGDO, m⁻²eV⁻¹ for DIT,
tubes/m for DCNT, K/W for RTH, J/K for CTH).

# Layout plan: `ring_osc_top` (180-nm CMOS, 1.8 V)

Die area target: 0.55 mm x 0.45 mm (inductor dominated).

## Floorplan (left to right, differential axis horizontal)

```
+---------------------------------------------------------------------+
| PAD p1   PAD n1        PAD p2   PAD n2     PAD vdd  PAD gnd  PAD ctl |
|  [L_out 29.8 nH]        [L_in 29.8 nH]      bias / trim DAC          |
|      |     |                |     |                                  |
|   SF drivers   <--  stage 2  <--  CG cascode pair  <-- [tank L_t 40 nH]|
|   (M4, Mt4)        (M2, Mt2)      (M1, M1c, Mt1)       [C_t + varactor]|
|   guard ring       guard ring     guard ring (deep n-well optional)   |
+---------------------------------------------------------------------+
```

* Keep the three inductors >= 50 um apart (edge to edge) and >= 30 um from any
  active device; no metal fill inside the inductor keep-out (use the PDK
  `NO_FILL` layer).  Patterned ground shield only if the PDK inductor model
  supports it (raises Q at 1 GHz by 10 to 20 %).
* Strict mirror symmetry of the differential pairs about the vertical axis:
  common-centroid M1a/M1b, M2a/M2b, M4a/M4b; identical routing length of
  d1a/d1b and oa/ob (the phase trim can absorb <= 15 deg of residual mismatch).
* The IDT pads (p1/n1, p2/n2) are 70 um octagonal pads with ESD diodes of
  <= 60 fF each (the budgeted `Cpar_in`); route p2/n2 on top metal only.
* Tank varactor: accumulation-mode MOS varactor 2 x 60 fF (Cmin) to 2 x 120 fF
  (Cmax), giving +/- 35 deg of loop phase trim (tank Q = 8).
* Supply: 2 x 10 pF MOS decoupling at vdd, star-connected ground, separate
  substrate contacts ring for the inductors.

## Verification sequence

1. DRC: `scripts/run_drc.sh` (Calibre) or Pegasus/PVS from Layout XL.
2. LVS: `scripts/run_lvs.sh` against the CDL exported from the schematic
   (File > Export > CDL); the Verilog-A resonator is a black box bound to the
   four pads (`LVS BOX phononic_ring_resonator`).
3. PEX: `scripts/run_pex.sh` (RC + coupling), then re-run
   `ocean/run_pss_pnoise.ocn` with `design()` pointing at the extracted view
   (`av_extracted` from Quantus or the `ring_osc_top_pex.sp` netlist).
4. Record pre- vs post-layout in `cadence/results/postlayout_summary.csv`
   with columns `metric,prelayout,postlayout` (f_osc, loop gain, PN@1k,
   PN@100k, I_dc, start-up time); `sim/collect_cadence_results.py` picks it up.

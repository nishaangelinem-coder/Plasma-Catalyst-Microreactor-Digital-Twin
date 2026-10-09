"""
Export the final design to Cadence Virtuoso / Spectre deliverables:
  cadence/circulator_core.scs    - Spectre netlist of the resonator wye with ideal 3-phase switch drive (PSS + PSP)
  cadence/circulator_full.scs    - Spectre netlist with the transistor-level phase generator and drivers
  cadence/psp_sparams.ocn        - OCEAN script: PSS (shooting) + PSP periodic S-parameters, IL/ISO/RL extraction
  cadence/build_schematics.il    - SKILL script that creates the schematic cellviews in a Virtuoso library
The device names (nch_rf, pch_rf, mimcap) are placeholders for the target PDK.
"""
import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.load_design import load_design

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAD = os.path.join(ROOT, 'cadence')


def core_scs(des, p):
    r, sw = des.res, des.sw
    txt = f"""// STM acoustic circulator - series-mode resonant junction core (Spectre)
// Auto-generated from results/design_final.json. Units SI. Direction = {des.direction:+d} (phase order of the pumps).
simulator lang=spectre
global 0
parameters fm={des.fm:.6e} frf=1.0e9 vdd=1.2 prf=-20 \\
    Csh={des.Cp:.4e} Csw={sw.Csw:.4e} Cpar={sw.Cpar:.4e} Wsw={sw.W:.1f}u Rg={sw.Rg:.0f} Rb={sw.Rb:.0f} Cdnw={sw.Cdnw:.2e} \\
    Rs={r.Rs} R0={r.R0} C0={r.C0:.4e} Rm={r.Rm:.5f} Lm={r.Lm:.6e} Cm={r.Cm:.4e}

// ---- mBVD LiNbO3 resonator (two-terminal) ----
subckt mbvd (a b)
  Rs (a ri) resistor r=Rs
  R0 (ri c0) resistor r=R0
  C0 (c0 b) capacitor c=C0
  Rm (ri m1) resistor r=Rm
  Lm (m1 m2) inductor l=Lm
  Cm (m2 b) capacitor c=Cm
ends mbvd

// ---- three-phase ideal square-wave pump on the switch gates (0 / 120 / 240 deg) ----
Vg0 (vg0 0) vsource type=pulse val0=0 val1=vdd period=1/fm width=0.5/fm rise=60p fall=60p delay=0.75/fm
Vg1 (vg1 0) vsource type=pulse val0=0 val1=vdd period=1/fm width=0.5/fm rise=60p fall=60p delay=0.75/fm+{1 if des.direction > 0 else 2}/(3*fm)
Vg2 (vg2 0) vsource type=pulse val0=0 val1=vdd period=1/fm width=0.5/fm rise=60p fall=60p delay=0.75/fm+{2 if des.direction > 0 else 1}/(3*fm)
Rstar (star 0) resistor r=10k
"""
    for n in range(3):
        q = n + 1
        txt += f"""// ---- branch {q} ----
PORT{q} (p{q} 0) port r=50 num={q} type=sine freq=frf dbm=prf
Csh{q} (p{q} 0) capacitor c=Csh
Xres{q} (p{q} m{q}) mbvd
Rb{q} (m{q} 0) resistor r=50k
Csw{q} (m{q} d{q}) capacitor c=Csw          // PDK: mimcap
Rg{q} (vg{n} g{q}) resistor r=Rg              // gate floating at RF (RF-switch configuration)
Rb{q} (b{q} star) resistor r=Rb               // triple-well body tied to the source
Cdnw{q} (b{q} 0) capacitor c=Cdnw             // deep-n-well capacitance (use the PDK triple-well device instead)
Msw{q} (d{q} g{q} star b{q}) nch_rf w=Wsw l=65n  // wide multi-finger switch (nch_rf_dnw / triple-well); stack 2 for higher power handling
Rd{q} (d{q} 0) resistor r=50k
{'Cpar%d (m%d star) capacitor c=Cpar' % (q, q) if sw.Cpar > 0 else ''}
"""
    txt += """// ---- analyses ----
pss  pss  fund=fm  harms=50  errpreset=conservative  method=gear2only  tstab=500n  maxacfreq=12G
psp  psp  sweeptype=absolute start=0.9G stop=1.1G lin=201 ports=[PORT1 PORT2 PORT3] portharmsvec=[0 0 0] donoise=no
// sidebands: repeat psp with portharmsvec=[1 0 0] and [-1 0 0]
// power handling: qpss/hb with prf swept, monitor V(d1,star) across the OFF switch
"""
    open(os.path.join(CAD, 'circulator_core.scs'), 'w').write(txt)


def full_scs(des, p):
    sw = des.sw
    txt = f"""// STM acoustic circulator - full transistor-level testbench (Spectre)
// Replace nmos65/pmos65 by the PDK's nch_rf/pch_rf and keep W/L; resonator and passives as in circulator_core.scs.
simulator lang=spectre
global 0 vdd!
parameters vdd=1.2 fm={des.fm:.6e} tclk=1/(6*fm) Wsw={sw.W:.1f}u

Vdd  (vdd!  0) vsource dc=vdd
Vclk (clk 0) vsource type=pulse val0=0 val1=vdd period=tclk width=tclk/2 rise=40p fall=40p
Vrst (rstn 0) vsource type=pulse val0=0 val1=vdd delay=3.5*tclk rise=50p fall=50p width=1 period=2

subckt inv (in out vdd vss)
  parameters wn=0.4u wp=0.8u
  Mp (out in vdd vdd) pch_rf w=wp l=65n
  Mn (out in vss vss) nch_rf w=wn l=65n
ends inv
subckt nand2 (a b out vdd vss)
  parameters wn=0.8u wp=0.8u
  Mpa (out a vdd vdd) pch_rf w=wp l=65n
  Mpb (out b vdd vdd) pch_rf w=wp l=65n
  Mna (out a x vss) nch_rf w=wn l=65n
  Mnb (x b vss vss) nch_rf w=wn l=65n
ends nand2
subckt tgate (in out c cb vdd vss)
  Mn (in c out vss) nch_rf w=0.4u l=65n
  Mp (in cb out vdd) pch_rf w=0.4u l=65n
ends tgate
subckt dff_rn (d clk clkb rstn q qb vdd vss)
  XT1 (d m1 clkb clk vdd vss) tgate
  XI1 (m1 m2 vdd vss) inv
  XN1 (m2 rstn m3 vdd vss) nand2
  XT2 (m3 m1 clk clkb vdd vss) tgate
  XT3 (m2 s1 clk clkb vdd vss) tgate
  XI3 (s1 q vdd vss) inv
  XI4 (q s2 vdd vss) inv
  XT4 (s2 s1 clkb clk vdd vss) tgate
  XI5 (q qb vdd vss) inv
ends dff_rn
subckt phasegen (clk rstn ph0 ph120 ph240 vdd vss)
  XIc1 (clk ckb0 vdd vss) inv wn=0.8u wp=1.6u
  XIc2 (ckb0 ck vdd vss) inv wn=1.6u wp=3.2u
  XIc3 (ck ckb vdd vss) inv wn=1.6u wp=3.2u
  XF0 (qb2 ck ckb rstn q0 qb0 vdd vss) dff_rn
  XF1 (q0 ck ckb rstn q1 qb1 vdd vss) dff_rn
  XF2 (q1 ck ckb rstn q2 qb2 vdd vss) dff_rn
  XB0a (q0 n0 vdd vss) inv
  XB0b (n0 ph0 vdd vss) inv wn=0.8u wp=1.6u
  XB1a (q2 n1 vdd vss) inv
  XB1b (n1 ph120 vdd vss) inv wn=0.8u wp=1.6u
  XB2a (qb1 n2 vdd vss) inv
  XB2b (n2 ph240 vdd vss) inv wn=0.8u wp=1.6u
ends phasegen
subckt vdrv (in out vdd vss)
  XD1 (in d1 vdd vss) inv wn=0.6u wp=1.2u
  XD2 (d1 d2 vdd vss) inv wn=1.8u wp=3.6u
  XD3 (d2 d3 vdd vss) inv wn=5.4u wp=10.8u
  XD4 (d3 d4 vdd vss) inv wn=16u wp=32u
  XD5 (d4 out vdd vss) inv wn=48u wp=96u
ends vdrv

Xpg (clk rstn ph0 ph120 ph240 vdd! 0) phasegen
Xd0 ({'ph0'} vg0 vdd! 0) vdrv
Xd1 ({'ph120' if des.direction > 0 else 'ph240'} vg1 vdd! 0) vdrv
Xd2 ({'ph240' if des.direction > 0 else 'ph120'} vg2 vdd! 0) vdrv
// ... branches identical to circulator_core.scs with the gates vg0..vg2 driven here ...
include "circulator_core.scs" section=branches

tran tran stop=1u errpreset=conservative
pss pss fund=fm harms=60 errpreset=conservative tstab=500n
psp psp sweeptype=absolute start=0.9G stop=1.1G lin=201 ports=[PORT1 PORT2 PORT3] portharmsvec=[0 0 0]
"""
    open(os.path.join(CAD, 'circulator_full.scs'), 'w').write(txt)


def ocean(des, p):
    txt = f""";; OCEAN script: PSS + PSP periodic S-parameters of the STM acoustic circulator (series-mode junction)
;; Usage in Virtuoso CIW:  load("psp_sparams.ocn")
simulator( 'spectre )
design( "circulator_lib" "tb_circulator_core" "schematic" )
resultsDir( "./psp_results" )
modelFile( '("/path/to/pdk/models/spectre/toplevel.scs" "tt") )
desVar( "fm" {des.fm:.6e} )
desVar( "Csh" {des.Cp:.4e} )
desVar( "Csw" {des.sw.Csw:.4e} )
desVar( "Wsw" "{des.sw.W:.0f}u" )
analysis( 'pss ?fund "fm" ?harms "50" ?errpreset "conservative" ?tstab "500n" ?maxacfreq "12G" )
analysis( 'psp ?sweeptype "absolute" ?start "0.9G" ?stop "1.1G" ?lin "201"
              ?ports list("/PORT1" "/PORT2" "/PORT3") ?portharmsvec list("0" "0" "0") ?donoise "no" )
option( 'reltol 1e-4 )
temp( 27 )
run()
selectResult( 'psp )
s21 = dB20( spm( 2 1 ) )   s32 = dB20( spm( 3 2 ) )   s13 = dB20( spm( 1 3 ) )
s12 = dB20( spm( 1 2 ) )   s23 = dB20( spm( 2 3 ) )   s31 = dB20( spm( 3 1 ) )
s11 = dB20( spm( 1 1 ) )   s22 = dB20( spm( 2 2 ) )   s33 = dB20( spm( 3 3 ) )
plot( s21 s12 s11 ?expr list("S21 (fwd)" "S12 (rev)" "S11") )
il  = -value( s21 1.0e9 )
iso = -value( s12 1.0e9 )
rl  = -value( s11 1.0e9 )
printf( "IL = %.2f dB  ISO = %.2f dB  RL = %.2f dB at 1 GHz\\n" il iso rl )
bw = bandwidth( -s12 20 "pass" )
printf( "20-dB isolation bandwidth = %.2f MHz\\n" bw/1e6 )
ocnPrint( ?output "./psp_results/sparams.csv" ?numberNotation 'scientific s21 s12 s11 s32 s23 s22 s13 s31 s33 )
selectResult( 'pss_td )
pdrv = -average( IT("/Vdd") ) * 1.2
printf( "Pump power (phase generator + drivers) = %.3f mW\\n" pdrv*1e3 )
"""
    open(os.path.join(CAD, 'psp_sparams.ocn'), 'w').write(txt)


def skill(des, p):
    r, sw = des.res, des.sw
    txt = f""";; SKILL: build the circulator schematic cellviews in library "circulator_lib"
;; load("build_schematics.il") in the CIW.  Requires analogLib and the target PDK library (edit pdkLib).
pdkLib = "tsmcN65"           ; <-- edit: PDK library with nch_rf / pch_rf / mimcap
libName = "circulator_lib"
unless( ddGetObj(libName) ddCreateLib(libName "./circulator_lib") )

procedure( mkInst(cv lib cell x y @optional (rot "R0") (props nil))
  let( (inst)
    inst = dbCreateInst(cv dbOpenCellViewByType(lib cell "symbol") nil list(x y) rot)
    foreach( p props dbReplaceProp(inst car(p) 'string cadr(p)) )
    inst ))

;; ---------------- mBVD resonator (two-terminal) ----------------
cv = dbOpenCellViewByType(libName "mbvd_linbo3" "schematic" "schematic" "w")
mkInst(cv "analogLib" "res" 0 0 "R0" list(list("r" "{r.Rs}")))          ; Rs
mkInst(cv "analogLib" "res" 1.5 1.0 "R0" list(list("r" "{r.R0}")))      ; R0
mkInst(cv "analogLib" "cap" 3.0 1.0 "R0" list(list("c" "{r.C0:.3e}")))  ; C0
mkInst(cv "analogLib" "res" 1.5 -1.0 "R0" list(list("r" "{r.Rm:.4f}")))  ; Rm
mkInst(cv "analogLib" "ind" 3.0 -1.0 "R0" list(list("l" "{r.Lm:.5e}")))  ; Lm
mkInst(cv "analogLib" "cap" 4.5 -1.0 "R0" list(list("c" "{r.Cm:.3e}")))  ; Cm
foreach( pn list("a" "b") dbCreatePin(cv dbCreateNet(cv pn) pn "inputOutput") )
schCheck(cv) dbSave(cv) dbClose(cv)

;; ---------------- branch: Csh, resonator, Rb, Csw, switch ----------------
cv = dbOpenCellViewByType(libName "branch" "schematic" "schematic" "w")
mkInst(cv pdkLib "mimcap" 0 -1.5 "R90" list(list("c" "Csh")))
mkInst(cv libName "mbvd_linbo3" 2.0 0)
mkInst(cv "analogLib" "res" 4.0 -1.5 "R90" list(list("r" "50k")))
mkInst(cv pdkLib "mimcap" 5.0 0 "R0" list(list("c" "Csw")))
mkInst(cv pdkLib "nch_rf" 7.0 -0.5 "R0" list(list("w" "{sw.W/20:.1f}u") list("l" "65n") list("nf" "20")))   ; {sw.W:.0f} um total, use the triple-well (dnw) variant
mkInst(cv "analogLib" "res" 6.0 1.5 "R0" list(list("r" "{sw.Rg:.0f}")))     ; Rg (gate floating at RF)
mkInst(cv "analogLib" "res" 8.0 -2.0 "R0" list(list("r" "{sw.Rb:.0f}")))    ; Rb (body tie to source)
foreach( pn list("port" "gate" "star") dbCreatePin(cv dbCreateNet(cv pn) pn "inputOutput") )
schCheck(cv) dbSave(cv) dbClose(cv)

;; ---------------- CMOS blocks ----------------
procedure( mkInv(name wn wp)
  let( (cv)
    cv = dbOpenCellViewByType(libName name "schematic" "schematic" "w")
    mkInst(cv pdkLib "pch_rf" 0 1.0 "R0" list(list("w" wp) list("l" "65n")))
    mkInst(cv pdkLib "nch_rf" 0 -1.0 "R0" list(list("w" wn) list("l" "65n")))
    foreach( pn list("in" "out" "vdd" "vss") dbCreatePin(cv dbCreateNet(cv pn) pn "inputOutput") )
    schCheck(cv) dbSave(cv) dbClose(cv) ))
mkInv("inv_x1" "0.4u" "0.8u")
mkInv("drv_s1" "0.6u" "1.2u") mkInv("drv_s2" "1.8u" "3.6u") mkInv("drv_s3" "5.4u" "10.8u")
mkInv("drv_s4" "16u" "32u")   mkInv("drv_s5" "48u" "96u")
cv = dbOpenCellViewByType(libName "vdrv" "schematic" "schematic" "w")
x = 0 foreach( c list("drv_s1" "drv_s2" "drv_s3" "drv_s4" "drv_s5") mkInst(cv libName c x 0) x = x + 2.0 )
schCheck(cv) dbSave(cv) dbClose(cv)
cv = dbOpenCellViewByType(libName "phasegen" "schematic" "schematic" "w")
for( i 0 2 mkInst(cv libName "dff_rn" i*3.0 0) )
schCheck(cv) dbSave(cv) dbClose(cv)

;; ---------------- top-level testbench ----------------
cv = dbOpenCellViewByType(libName "tb_circulator_core" "schematic" "schematic" "w")
for( i 1 3
  mkInst(cv "analogLib" "port" -2.0 -(i*3.0) "R0" list(list("r" "50") list("num" sprintf(nil "%d" i)) list("srcType" "sine") list("freq" "frf") list("dbm" "prf")))
  mkInst(cv libName "branch" 0 -(i*3.0)) )
mkInst(cv libName "phasegen" 8.0 0)
for( i 0 2 mkInst(cv libName "vdrv" 10.0 -(i*2.0)) )
mkInst(cv "analogLib" "res" 6.0 -10 "R90" list(list("r" "10k")))   ; Rstar
schCheck(cv) dbSave(cv) dbClose(cv)
printf("circulator_lib schematics created. Wire the nets per cadence/README.md, then run psp_sparams.ocn\\n")
"""
    open(os.path.join(CAD, 'build_schematics.il'), 'w').write(txt)


if __name__ == '__main__':
    des, p = load_design()
    core_scs(des, p); full_scs(des, p); ocean(des, p); skill(des, p)
    print('cadence deliverables written to', CAD)

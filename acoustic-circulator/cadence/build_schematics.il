;; SKILL: build the circulator schematic cellviews in library "circulator_lib"
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
mkInst(cv "analogLib" "res" 0 0 "R0" list(list("r" "0.5")))          ; Rs
mkInst(cv "analogLib" "res" 1.5 1.0 "R0" list(list("r" "0.3")))      ; R0
mkInst(cv "analogLib" "cap" 3.0 1.0 "R0" list(list("c" "1.200e-12")))  ; C0
mkInst(cv "analogLib" "res" 1.5 -1.0 "R0" list(list("r" "1.1253")))  ; Rm
mkInst(cv "analogLib" "ind" 3.0 -1.0 "R0" list(list("l" "9.49729e-08")))  ; Lm
mkInst(cv "analogLib" "cap" 4.5 -1.0 "R0" list(list("c" "3.000e-13")))  ; Cm
foreach( pn list("a" "b") dbCreatePin(cv dbCreateNet(cv pn) pn "inputOutput") )
schCheck(cv) dbSave(cv) dbClose(cv)

;; ---------------- branch: Csh, resonator, Rb, Csw, switch ----------------
cv = dbOpenCellViewByType(libName "branch" "schematic" "schematic" "w")
mkInst(cv pdkLib "mimcap" 0 -1.5 "R90" list(list("c" "Csh")))
mkInst(cv libName "mbvd_linbo3" 2.0 0)
mkInst(cv "analogLib" "res" 4.0 -1.5 "R90" list(list("r" "50k")))
mkInst(cv pdkLib "mimcap" 5.0 0 "R0" list(list("c" "Csw")))
mkInst(cv pdkLib "nch_rf" 7.0 -0.5 "R0" list(list("w" "10.6u") list("l" "65n") list("nf" "20")))   ; 211 um total, use the triple-well (dnw) variant
mkInst(cv "analogLib" "res" 6.0 1.5 "R0" list(list("r" "3000")))     ; Rg (gate floating at RF)
mkInst(cv "analogLib" "res" 8.0 -2.0 "R0" list(list("r" "20000")))    ; Rb (body tie to source)
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
printf("circulator_lib schematics created. Wire the nets per cadence/README.md, then run psp_sparams.ocn\n")

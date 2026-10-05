;; =============================================================================
;; build_schematics.il -- SKILL: build every schematic of the CFET circuit
;; validation flow programmatically in CFET_LIB.
;;
;;   inv_cfet_<plat>      CFET inverter: n + p device, Cstack, Cout, Rlocal_n/p
;;   ro5/ro7/ro9_cfet_<plat>  odd ring oscillators of inverter instances
;;   tb_<device>          nine device testbenches (vdc VGS, vdc VDS, gnd)
;;   tb_inv_cfet_<plat>   inverter testbench (vdc VDD, vpulse VIN, cap CLOAD)
;;   tb_ro5_cfet_<plat>   ring-oscillator testbench (vdc VDD; ic set in ADE)
;;   (+ tb_ro7_/tb_ro9_   same for the 7 and 9 stage rings)
;;
;; Usage (CIW), after create_cfet_lib.il has been run:
;;   load(strcat(getShellEnvVar("CFET_ROOT") "/cadence/skill/build_schematics.il"))
;;   cfetBuildAll()
;;   cfetBuildPlatform("tmd")        ; one platform only
;;
;; Design: everything is data driven from cfetPlatforms (one DPL record per
;; platform) and cfetDeviceNominal (fixed material parameters per device cell).
;; Connectivity is made "by name": each instance terminal gets a short wire stub
;; whose label is the net name; schCheck() then builds the nets. This avoids
;; any dependency on the pin geometry of the analogLib symbols. Instance
;; parameter values are design-variable expressions (VDD, VGS, VDS, CLOAD,
;; CSTACK, COUT, RLOCAL, Wn, Wp, Lg, NNSn, NNSp, VTHN, VTHP, MUN, MUP, RCN, RCP,
;; RTH, CTH, DIT, DCNT, FMET, TEMP) that ADE picks up with "Copy From Cellview".
;;
;; All coordinates are >= 0 and points are written list(x y) to avoid the SKILL
;; `list(1 -2)` == `list(1-2)` pitfall.
;; =============================================================================

unless(boundp('CFET_LIB_NAME) CFET_LIB_NAME = "CFET_LIB")
;; t -> ring oscillators start by a 1 % VTHN offset on stage 1 instead of ic()
unless(boundp('CFET_RO_MISMATCH_STARTUP) CFET_RO_MISMATCH_STARTUP = nil)
unless(boundp('cfetMsg)
  procedure(cfetMsg(fmt @rest args)
    printf("[cfet] %s\n" apply('sprintf cons(nil cons(fmt args))))))

;; Schematic grid and wire stub length
CFET_GRID = 0.0625
CFET_STUB = 0.25

;; ---------------------------------------------------------------------------
;; 1. Data: platforms, devices, nominal parameters
;; ---------------------------------------------------------------------------
;; One record per platform. Values are strings exactly as typed in a CDF form.
;;   nCell/pCell : device cells            vdd : nominal VDD (design var default)
;;   cstack/cout/rlocal : CDF defaults of the inverter cell (mid-range values)
;;   roStop/roMaxstep   : transient settings of the RO testbench (documentation
;;                        here; used by ocean/ro_tran.ocn)
;;   nVars/pVars : (param designVariable) pairs set on the n / p device of the
;;                 inverter and of the device testbench
cfetPlatforms = list(
  list(nil 'name "si"   'label "CFET-Si"   'nCell "gaa_n"  'pCell "gaa_p"
       'vdd "0.7" 'cstack "0.05f" 'cout "0.3f" 'rlocal "10"
       'roStop "5n" 'roMaxstep "1p"
       'nVars list(list("L" "Lg") list("NNS" "NNSn") list("WNS" "WNS") list("VTH0" "VTHN")
                   list("MU0" "MUN") list("RSW" "RSW") list("RDW" "RSW"))
       'pVars list(list("L" "Lg") list("NNS" "NNSp") list("WNS" "WNS") list("VTH0" "VTHP")
                   list("MU0" "MUP") list("RSW" "RSW") list("RDW" "RSW")))
  list(nil 'name "sige" 'label "CFET-SiGe" 'nCell "gaa_n"  'pCell "sige_p"
       'vdd "0.7" 'cstack "0.05f" 'cout "0.3f" 'rlocal "10"
       'roStop "5n" 'roMaxstep "1p"
       'nVars list(list("L" "Lg") list("NNS" "NNSn") list("WNS" "WNS") list("VTH0" "VTHN")
                   list("MU0" "MUN") list("RSW" "RSW") list("RDW" "RSW"))
       'pVars list(list("L" "Lg") list("NNS" "NNSp") list("WNS" "WNS") list("VTH0" "VTHP")
                   list("MU0" "MUP") list("RSW" "RSW") list("RDW" "RSW")))
  list(nil 'name "tmd"  'label "CFET-TMD"  'nCell "mos2_n" 'pCell "wse2_p"
       'vdd "0.5" 'cstack "0.03f" 'cout "0.3f" 'rlocal "50"
       'roStop "50n" 'roMaxstep "10p"
       'nVars list(list("W" "Wn") list("L" "Lg") list("VTH0" "VTHN") list("MU0" "MUN")
                   list("RC" "RCN") list("DIT" "DIT"))
       'pVars list(list("W" "Wp") list("L" "Lg") list("VTH0" "VTHP") list("MU0" "MUP")
                   list("RC" "RCP") list("DIT" "DIT")))
  list(nil 'name "cnt"  'label "CFET-CNT"  'nCell "cnt_n"  'pCell "cnt_p"
       'vdd "0.6" 'cstack "0.03f" 'cout "0.3f" 'rlocal "50"
       'roStop "5n" 'roMaxstep "1p"
       'nVars list(list("W" "Wn") list("L" "Lg") list("VTH0" "VTHN") list("DCNT" "DCNT")
                   list("FMET" "FMET") list("RC" "RCN"))
       'pVars list(list("W" "Wp") list("L" "Lg") list("VTH0" "VTHP") list("DCNT" "DCNT")
                   list("FMET" "FMET") list("RC" "RCP")))
  list(nil 'name "gan"  'label "CFET-GaN"  'nCell "gan_n"  'pCell "gan_p"
       'vdd "1.2" 'cstack "0.1f" 'cout "1f" 'rlocal "20"
       'roStop "20n" 'roMaxstep "5p"
       'nVars list(list("W" "Wn") list("L" "Lg") list("VTH0" "VTHN") list("MU0" "MUN")
                   list("RTH" "RTH") list("CTH" "CTH"))
       'pVars list(list("W" "Wp") list("L" "Lg") list("VTH0" "VTHP") list("MU0" "MUP")
                   list("RTH" "RTH") list("CTH" "CTH")))
)

;; Fixed (non-swept) material parameters per device cell, SI units, identical
;; to netlists/spectre/*.scs. Parameters driven by design variables (nVars /
;; pVars) are deliberately absent here.
cfetDeviceNominal = list(
  list("gaa_n" list("TNS" "5n") list("N0" "1.10") list("ETA" "0.06")
                list("COX" "0.040") list("VSAT" "1e5") list("LAMBDA" "0.05") list("CGSO" "1e-10") list("CGDO" "1e-10")
                list("TNOM" "300") list("MUEXP" "1.5") list("KVTH" "-1e-3"))
  list("gaa_p" list("TNS" "5n") list("N0" "1.10") list("ETA" "0.07")
                list("COX" "0.040") list("VSAT" "8e4") list("LAMBDA" "0.05") list("CGSO" "1e-10") list("CGDO" "1e-10")
                list("TNOM" "300") list("MUEXP" "1.5") list("KVTH" "-1e-3"))
  list("sige_p" list("TNS" "5n") list("N0" "1.12") list("ETA" "0.08")
                list("COX" "0.040") list("VSAT" "8e4") list("LAMBDA" "0.06") list("CGSO" "1e-10") list("CGDO" "1e-10")
                list("TNOM" "300") list("MUEXP" "1.5") list("KVTH" "-1e-3"))
  list("mos2_n" list("N0" "1.15") list("ETA" "0.08") list("COX" "0.020") list("CQ" "0.030")
                list("VSAT" "3e4") list("LAMBDA" "0.10") list("RSW" "0") list("RDW" "0")
                list("CGSO" "5e-11") list("CGDO" "5e-11")
                list("TNOM" "300") list("MUEXP" "1.0") list("KVTH" "-1.5e-3"))
  list("wse2_p" list("N0" "1.20") list("ETA" "0.09") list("COX" "0.020") list("CQ" "0.025")
                list("VSAT" "2.5e4") list("LAMBDA" "0.12") list("RSW" "0") list("RDW" "0")
                list("CGSO" "5e-11") list("CGDO" "5e-11")
                list("TNOM" "300") list("MUEXP" "1.0") list("KVTH" "-1.5e-3"))
  list("cnt_n"  list("N0" "1.05") list("ETA" "0.04") list("COX" "0.020") list("TTR" "0.70")
                list("ALPHA" "0.60") list("RSW" "0") list("RDW" "0")
                list("CGSO" "4e-11") list("CGDO" "4e-11")
                list("TNOM" "300") list("MUEXP" "0") list("KVTH" "-1e-3"))
  list("cnt_p"  list("N0" "1.05") list("ETA" "0.05") list("COX" "0.020") list("TTR" "0.65")
                list("ALPHA" "0.60") list("RSW" "0") list("RDW" "0")
                list("CGSO" "4e-11") list("CGDO" "4e-11")
                list("TNOM" "300") list("MUEXP" "0") list("KVTH" "-1e-3"))
  list("gan_n"  list("N0" "1.20") list("ETA" "0.03") list("COX" "0.015") list("VSAT" "2e5")
                list("LAMBDA" "0.02") list("RSW" "3e-4") list("RDW" "3e-4")
                list("CGSO" "1.5e-10") list("CGDO" "1.5e-10")
                list("TNOM" "300") list("MUEXP" "1.5") list("KVTH" "-2e-3"))
  list("gan_p"  list("N0" "1.30") list("ETA" "0.04") list("COX" "0.015") list("VSAT" "5e4")
                list("LAMBDA" "0.03") list("RSW" "1e-3") list("RDW" "1e-3")
                list("CGSO" "1.5e-10") list("CGDO" "1.5e-10")
                list("TNOM" "300") list("MUEXP" "1.5") list("KVTH" "-2e-3"))
)

;; Ring lengths built for every platform
cfetRingStages = list(5 7 9)

procedure(cfetPlatform(name)
  car(exists(p cfetPlatforms p->name == name)))

;; Device -> (platform polarity): the testbench of a device uses the design
;; variables of its platform ('nVars or 'pVars).
procedure(cfetDeviceRole(cell)
  let((hit)
    foreach(p cfetPlatforms
      when(p->nCell == cell && !hit hit = list(p "n"))
      when(p->pCell == cell && !hit hit = list(p "p")))
    hit))

;; ---------------------------------------------------------------------------
;; 2. Low-level helpers
;; ---------------------------------------------------------------------------
procedure(cfetSnap(v) CFET_GRID * round(v / CFET_GRID))

;; Open a schematic for (over)writing: "w" creates an empty cellview.
procedure(cfetOpenSchematic(cell)
  let((cv)
    cv = dbOpenCellViewByType(CFET_LIB_NAME cell "schematic" "schematic" "w")
    unless(cv error("cannot open %s/%s/schematic" CFET_LIB_NAME cell))
    cv))

;; Place an instance by master name; returns the instance.
;; (schCreateInst(cv masterCv name origin orient) is the alternative when the
;;  master cellview is already open: masterCv = dbOpenCellViewByType(lib cell "symbol").)
procedure(cfetInst(cv lib cell name x y @optional (orient "R0"))
  let((inst)
    inst = dbCreateInstByMasterName(cv lib cell "symbol" name list(x y) orient)
    unless(inst error("dbCreateInstByMasterName failed: %s/%s as %s in %s" lib cell name cv~>cellName))
    inst))

;; Set CDF instance parameters from a list of (name value) string pairs.
procedure(cfetSetParams(inst pairs)
  foreach(p pairs dbReplaceProp(inst car(p) "string" cadr(p)))
  inst)

;; Absolute position of an instance terminal: the centre of the pin figure of
;; the master symbol, transformed by the instance transform.
procedure(cfetTermPoint(inst termName)
  let((term fig)
    term = if(termName
              car(exists(tm inst~>master~>terminals tm~>name == termName))
              car(inst~>master~>terminals))
    unless(term error("terminal %L not found on %s" termName inst~>master~>cellName))
    fig = car(term~>pins)~>fig
    dbTransformPoint(centerBox(fig~>bBox) inst~>transform)))

;; Connect-by-name: draw a stub wire away from the terminal and label it.
;; The stub direction is away from the instance centre, snapped to an axis.
procedure(cfetConnect(cv inst termName netName)
  let((pt ctr dx dy end wires)
    pt  = cfetTermPoint(inst termName)
    ctr = centerBox(inst~>bBox)
    dx  = xCoord(pt) - xCoord(ctr)
    dy  = yCoord(pt) - yCoord(ctr)
    ;; minus(CFET_STUB) rather than -CFET_STUB: `CFET_STUB -CFET_STUB` would be
    ;; parsed as a subtraction by the SKILL reader.
    end = if(abs(dx) >= abs(dy)
             list(xCoord(pt) + if(dx >= 0 CFET_STUB minus(CFET_STUB)) yCoord(pt))
             list(xCoord(pt) yCoord(pt) + if(dy >= 0 CFET_STUB minus(CFET_STUB))))
    end = list(cfetSnap(xCoord(end)) cfetSnap(yCoord(end)))
    ;; schCreateWire(cv mode routeMethod points startSnap endSnap width) -> list of wires
    wires = schCreateWire(cv "draw" "full" list(pt end) CFET_GRID CFET_GRID 0.0)
    when(wires
      schCreateWireLabel(cv car(wires) end netName "lowerLeft" "R0" "stick" CFET_GRID nil))
    wires))

;; Schematic pin (basic ipin/opin/iopin) at (x y), connected to the net of the
;; same name. schCreatePin(cv master name direction offsheet location orient)
procedure(cfetPin(cv name dir x y)
  let((masterCell master pinInst)
    masterCell = case(dir ("input" "ipin") ("output" "opin") (t "iopin"))
    master = dbOpenCellViewByType("basic" masterCell "symbol")
    unless(master error("basic/%s/symbol not found -- is `basic` in cds.lib?" masterCell))
    pinInst = schCreatePin(cv master name dir nil list(x y) "R0")
    unless(pinInst error("schCreatePin failed for %s" name))
    cfetConnect(cv pinInst nil name)
    pinInst))

;; Free text note (documentation inside the schematic)
procedure(cfetNote(cv x y text)
  when(isCallable('schCreateNoteLabel)
    schCreateNoteLabel(cv list(x y) text "lowerLeft" "R0" "stick" CFET_GRID)))

;; Finish: check, save, close. schCheck returns nil when there are no errors
;; (warnings about floating stubs are expected to be absent because every
;; stub is labelled).
procedure(cfetFinish(cv)
  let((rc)
    rc = schCheck(cv)
    cfetMsg("%s: schCheck -> %L (nil = clean)" cv~>cellName rc)
    dbSave(cv)
    dbClose(cv)
    rc))

;; Symbol pin helper: pin square on ("pin" "drawing") + terminal + name label.
procedure(cfetSymPin(cv name x y dir)
  let((fig)
    fig = dbCreateRect(cv list("pin" "drawing")
            list(list(x - 0.0625 y - 0.0625) list(x + 0.0625 y + 0.0625)))
    schCreateSymbolPin(cv fig name dir)
    schCreateSymbolLabel(cv list(x + 0.1 y + 0.1) "pin name" name
                         "lowerLeft" "R0" "stick" 0.0625)
    fig))

;; Generic box symbol (deterministic; replaces the GUI "Create -> Cellview ->
;; From Cellview" step). Pins: left/right/top/bottom name lists.
procedure(cfetBoxSymbol(cell leftPins rightPins topPins bottomPins)
  let((cv w h n i x y allPins)
    w = 2.0
    h = 0.5 * max(2 max(length(leftPins) length(rightPins)) + 1)
    cv = dbOpenCellViewByType(CFET_LIB_NAME cell "symbol" "schematicSymbol" "w")
    unless(cv error("cannot open %s/%s/symbol" CFET_LIB_NAME cell))
    dbCreateRect(cv list("device" "drawing") list(list(0.5 0.5) list(w + 0.5 h + 0.5)))
    n = length(leftPins) i = 0
    foreach(p leftPins
      i = i + 1  y = cfetSnap(0.5 + h * i / (n + 1.0))
      dbCreateLine(cv list("device" "drawing") list(list(0.0 y) list(0.5 y)))
      cfetSymPin(cv p 0.0 y "input"))
    n = length(rightPins) i = 0
    foreach(p rightPins
      i = i + 1  y = cfetSnap(0.5 + h * i / (n + 1.0))
      dbCreateLine(cv list("device" "drawing") list(list(w + 0.5 y) list(w + 1.0 y)))
      cfetSymPin(cv p w + 1.0 y "output"))
    n = length(topPins) i = 0
    foreach(p topPins
      i = i + 1  x = cfetSnap(0.5 + w * i / (n + 1.0))
      dbCreateLine(cv list("device" "drawing") list(list(x h + 0.5) list(x h + 1.0)))
      cfetSymPin(cv p x h + 1.0 "inputOutput"))
    n = length(bottomPins) i = 0
    foreach(p bottomPins
      i = i + 1  x = cfetSnap(0.5 + w * i / (n + 1.0))
      dbCreateLine(cv list("device" "drawing") list(list(x 0.0) list(x 0.5)))
      cfetSymPin(cv p x 0.0 "inputOutput"))
    dbCreateRect(cv list("instance" "drawing") list(list(0.0 0.0) list(w + 1.0 h + 1.0)))
    schCreateSymbolLabel(cv list(0.5 h + 0.55) "instance name" "[@instanceName]"
                         "lowerLeft" "R0" "stick" 0.0625)
    schCreateSymbolLabel(cv list(0.5 0.3) "device annotate" "[@partName]"
                         "lowerLeft" "R0" "stick" 0.0625)
    allPins = append(leftPins append(rightPins append(topPins bottomPins)))
    dbReplaceProp(cv "pinOrder" "string" buildString(allPins " "))
    dbReplaceProp(cv "partName" "string" cell)
    dbReplaceProp(cv "instNamePrefix" "string" "I")
    dbSave(cv)
    dbClose(cv)
    cfetMsg("%s: symbol written (%s)" cell buildString(allPins " "))
    t))

;; Cell CDF with parameters that the schematic uses through pPar("NAME").
procedure(cfetCellCDF(cell pairs)
  let((cellId cdfId)
    cellId = ddGetObj(CFET_LIB_NAME cell)
    cdfId = cdfGetBaseCellCDF(cellId) || cdfCreateBaseCellCDF(cellId)
    foreach(p pairs
      unless(cdfFindParamByName(cdfId car(p))
        cdfCreateParam(cdfId ?name car(p) ?prompt car(p) ?type "string"
                       ?defValue cadr(p) ?display "t" ?editable "t"
                       ?paramType "instance")))
    cdfId~>instNamePrefix = "I"
    cdfSaveCDF(cdfId)
    cdfId))

;; Parameter list of a device instance: platform variables + fixed nominal set
procedure(cfetDeviceParams(cell vars)
  append(vars cdr(assoc(cell cfetDeviceNominal))))

;; ("VTH0" "VTHN") -> ("VTH0" "pPar(\"VTHN\")")  (inside the inverter cell)
procedure(cfetPParVars(vars)
  foreach(mapcar v vars list(car(v) sprintf(nil "pPar(\"%s\")" cadr(v)))))

;; Unique design variables of a platform's devices as (name name) CDF entries
procedure(cfetInverterVarParams(plat)
  let((names)
    foreach(v append(plat->nVars plat->pVars)
      unless(member(cadr(v) names) names = append(names list(cadr(v)))))
    foreach(mapcar nm names list(nm nm))))

;; ---------------------------------------------------------------------------
;; 3. Inverter cell  inv_cfet_<plat>
;; ---------------------------------------------------------------------------
;;   in  --+-- g MP (pCell)  s,b -> vdd      d -> pd --Rlocal_p-- out
;;         +-- g MN (nCell)  s,b -> vss      d -> nd --Rlocal_n-- out
;;   Cstack between pd and nd (vertical n/p stack coupling capacitance)
;;   Cout  between out and vss (output/local-interconnect load)
;; Values come from the cell CDF (CSTACK COUT RLOCAL) via pPar().
procedure(cfetBuildInverter(plat)
  let((cell cv mp mn rp rn cs co)
    cell = strcat("inv_cfet_" plat->name)
    cfetMsg("building %s" cell)
    ;; Cell CDF: parasitics with mid-range defaults + every design variable used
    ;; by the two devices (default = the design variable of the same name, so a
    ;; testbench instance left at its defaults netlists as VTHN=VTHN etc.).
    ;; Declaring them as subcircuit parameters is what lets the Spectre
    ;; `statistics { mismatch { vary VTHN ... } }` block (ade/mc_statistics.scs)
    ;; draw an independent sample for every inverter instance.
    cfetCellCDF(cell append(list(list("CSTACK" plat->cstack)
                                 list("COUT"   plat->cout)
                                 list("RLOCAL" plat->rlocal))
                            cfetInverterVarParams(plat)))
    cv = cfetOpenSchematic(cell)
    ;; devices
    mp = cfetInst(cv CFET_LIB_NAME plat->pCell "MP" 4.0 6.0)
    mn = cfetInst(cv CFET_LIB_NAME plat->nCell "MN" 4.0 2.0)
    cfetSetParams(mp cfetDeviceParams(plat->pCell cfetPParVars(plat->pVars)))
    cfetSetParams(mn cfetDeviceParams(plat->nCell cfetPParVars(plat->nVars)))
    cfetConnect(cv mp "g" "in")  cfetConnect(cv mp "s" "vdd")
    cfetConnect(cv mp "b" "vdd") cfetConnect(cv mp "d" "pd")
    cfetConnect(cv mn "g" "in")  cfetConnect(cv mn "s" "vss")
    cfetConnect(cv mn "b" "vss") cfetConnect(cv mn "d" "nd")
    ;; CFET parasitics (analogLib res/cap; CDF parameter names r / c)
    rp = cfetInst(cv "analogLib" "res" "Rlocal_p" 7.5 6.0 "R90")
    rn = cfetInst(cv "analogLib" "res" "Rlocal_n" 7.5 2.0 "R90")
    cs = cfetInst(cv "analogLib" "cap" "Cstack"   5.5 4.0)
    co = cfetInst(cv "analogLib" "cap" "Cout"     10.0 2.0)
    cfetSetParams(rp list(list("r" "pPar(\"RLOCAL\")")))
    cfetSetParams(rn list(list("r" "pPar(\"RLOCAL\")")))
    cfetSetParams(cs list(list("c" "pPar(\"CSTACK\")")))
    cfetSetParams(co list(list("c" "pPar(\"COUT\")")))
    cfetConnect(cv rp "PLUS" "pd")  cfetConnect(cv rp "MINUS" "out")
    cfetConnect(cv rn "PLUS" "nd")  cfetConnect(cv rn "MINUS" "out")
    cfetConnect(cv cs "PLUS" "pd")  cfetConnect(cv cs "MINUS" "nd")
    cfetConnect(cv co "PLUS" "out") cfetConnect(cv co "MINUS" "vss")
    ;; pins
    cfetPin(cv "in"  "input"       1.0 4.0)
    cfetPin(cv "out" "output"      12.0 4.0)
    cfetPin(cv "vdd" "inputOutput" 4.0 9.0)
    cfetPin(cv "vss" "inputOutput" 4.0 0.5)
    cfetNote(cv 1.0 10.0 sprintf(nil "%s inverter: %s over %s, Cstack=%s Cout=%s Rlocal=%s"
                                 plat->label plat->pCell plat->nCell
                                 plat->cstack plat->cout plat->rlocal))
    cfetFinish(cv)
    cfetBoxSymbol(cell list("in") list("out") list("vdd") list("vss"))
    cell))

;; ---------------------------------------------------------------------------
;; 4. Ring oscillators  roN_cfet_<plat>   (N odd)
;; ---------------------------------------------------------------------------
;; Nodes n1..nN; inverter k drives n_k from n_(k-1); inverter 1 is driven by nN
;; (ring closed). Pin `out` = n1. CSTACK/COUT/RLOCAL are passed through as
;; design variables so Assembler can sweep them at top level.
procedure(cfetBuildRing(plat n)
  let((cell cv inv inst inNet outNet x)
    cell = sprintf(nil "ro%d_cfet_%s" n plat->name)
    inv  = strcat("inv_cfet_" plat->name)
    cfetMsg("building %s" cell)
    cv = cfetOpenSchematic(cell)
    for(k 1 n
      inNet  = if(k == 1 sprintf(nil "n%d" n) sprintf(nil "n%d" k - 1))
      outNet = sprintf(nil "n%d" k)
      x = 1.0 + 4.0 * (k - 1)
      inst = cfetInst(cv CFET_LIB_NAME inv sprintf(nil "I%d" k) x 4.0)
      cfetSetParams(inst list(list("CSTACK" "CSTACK") list("COUT" "COUT") list("RLOCAL" "RLOCAL")))
      ;; optional start-up by 1 % VTH mismatch on the first stage (brief step 23);
      ;; default is the initial-condition kick applied in ADE/OCEAN (ic /out 0)
      when(k == 1 && CFET_RO_MISMATCH_STARTUP
        cfetSetParams(inst list(list("VTHN" "1.01*VTHN"))))
      cfetConnect(cv inst "in"  inNet)
      cfetConnect(cv inst "out" outNet)
      cfetConnect(cv inst "vdd" "vdd")
      cfetConnect(cv inst "vss" "vss"))
    ;; pins: out is node n1 (net alias through a labelled stub on the pin)
    x = 1.0 + 4.0 * n
    cfetPin(cv "n1"  "output"      x 4.0)
    cfetPin(cv "vdd" "inputOutput" 2.0 8.0)
    cfetPin(cv "vss" "inputOutput" 2.0 0.5)
    cfetNote(cv 1.0 9.0 sprintf(nil "%d-stage %s ring oscillator; start-up by ic n1=0 (ADE Convergence Aids) or 1%% VTH mismatch on I1"
                                n plat->label))
    cfetFinish(cv)
    cfetBoxSymbol(cell nil list("n1") list("vdd") list("vss"))
    cell))

;; ---------------------------------------------------------------------------
;; 5. Device testbench  tb_<device>
;; ---------------------------------------------------------------------------
;;   VG: vdc PLUS->g MINUS->gnd, value  VGS (n) / -VGS (p)
;;   VD: vdc PLUS->d MINUS->gnd, value  VDS (n) / -VDS (p)
;;   s and b -> gnd.  Drain current = -I(VD:PLUS) for n, +I(VD:PLUS) for p
;;   (the OCEAN scripts take the sign from the device polarity).
procedure(cfetBuildDeviceTB(cell)
  let((role plat pol tb cv dut vg vd g sgn)
    role = cfetDeviceRole(cell)
    unless(role error("device %s is not in cfetPlatforms" cell))
    plat = car(role) pol = cadr(role)
    tb = strcat("tb_" cell)
    cfetMsg("building %s" tb)
    cv = cfetOpenSchematic(tb)
    dut = cfetInst(cv CFET_LIB_NAME cell "M0" 5.0 4.0)
    cfetSetParams(dut cfetDeviceParams(cell if(pol == "n" plat->nVars plat->pVars)))
    sgn = if(pol == "n" "" "-")
    vg = cfetInst(cv "analogLib" "vdc" "VG" 1.0 4.0)
    vd = cfetInst(cv "analogLib" "vdc" "VD" 9.0 4.0)
    cfetSetParams(vg list(list("vdc" strcat(sgn "VGS"))))
    cfetSetParams(vd list(list("vdc" strcat(sgn "VDS"))))
    g = cfetInst(cv "analogLib" "gnd" "gnd0" 5.0 0.5)
    cfetConnect(cv vg "PLUS" "g")  cfetConnect(cv vg "MINUS" "gnd!")
    cfetConnect(cv vd "PLUS" "d")  cfetConnect(cv vd "MINUS" "gnd!")
    cfetConnect(cv dut "g" "g") cfetConnect(cv dut "d" "d")
    cfetConnect(cv dut "s" "gnd!") cfetConnect(cv dut "b" "gnd!")
    cfetNote(cv 1.0 8.0 sprintf(nil "%s (%s, %s-type): VGS/VDS design variables; Id = %sI(VD:PLUS)"
                                cell plat->label pol if(pol == "n" "-" "+")))
    cfetFinish(cv)
    tb))

;; ---------------------------------------------------------------------------
;; 6. Inverter testbench  tb_inv_cfet_<plat>
;; ---------------------------------------------------------------------------
;;   VDD : vdc  = VDD
;;   VIN : vpulse v1=0 v2=VDD td=100p tr=5p tf=5p pw=500p per=1n  (spec)
;;   I0  : inverter (CSTACK COUT RLOCAL design variables)
;;   CL  : cap = CLOAD
procedure(cfetBuildInverterTB(plat)
  let((tb inv cv vdd vin inst cl)
    tb  = strcat("tb_inv_cfet_" plat->name)
    inv = strcat("inv_cfet_" plat->name)
    cfetMsg("building %s" tb)
    cv = cfetOpenSchematic(tb)
    vdd = cfetInst(cv "analogLib" "vdc" "VDD" 1.0 7.0)
    vin = cfetInst(cv "analogLib" "vpulse" "VIN" 1.0 3.0)
    cfetSetParams(vdd list(list("vdc" "VDD")))
    cfetSetParams(vin list(list("v1" "0") list("v2" "VDD") list("td" "100p")
                           list("tr" "5p") list("tf" "5p") list("pw" "500p") list("per" "1n")))
    inst = cfetInst(cv CFET_LIB_NAME inv "I0" 5.0 4.0)
    cfetSetParams(inst list(list("CSTACK" "CSTACK") list("COUT" "COUT") list("RLOCAL" "RLOCAL")))
    cl = cfetInst(cv "analogLib" "cap" "CL" 10.0 3.0)
    cfetSetParams(cl list(list("c" "CLOAD")))
    cfetInst(cv "analogLib" "gnd" "gnd0" 5.0 0.5)
    cfetConnect(cv vdd "PLUS" "vdd") cfetConnect(cv vdd "MINUS" "gnd!")
    cfetConnect(cv vin "PLUS" "in")  cfetConnect(cv vin "MINUS" "gnd!")
    cfetConnect(cv inst "in" "in")   cfetConnect(cv inst "out" "out")
    cfetConnect(cv inst "vdd" "vdd") cfetConnect(cv inst "vss" "gnd!")
    cfetConnect(cv cl "PLUS" "out")  cfetConnect(cv cl "MINUS" "gnd!")
    cfetNote(cv 1.0 9.0 sprintf(nil "%s inverter TB: VTC = dc sweep of VIN dc value; tran stop 2n maxstep %s"
                                plat->label plat->roMaxstep))
    cfetFinish(cv)
    tb))

;; ---------------------------------------------------------------------------
;; 7. Ring-oscillator testbench  tb_roN_cfet_<plat>
;; ---------------------------------------------------------------------------
;;   VDD : vdc = VDD ; I0 : ring ; node `out` (= n1 inside the ring).
;;   Start-up: analogLib has no "ic" cell; the initial condition is applied in
;;   ADE (Setup -> Simulation -> Convergence Aids -> Initial Condition, node
;;   /out = 0) or in OCEAN with ic("/out" 0.0) -- see ocean/ro_tran.ocn.
procedure(cfetBuildRingTB(plat n)
  let((tb ring cv vdd inst)
    tb   = sprintf(nil "tb_ro%d_cfet_%s" n plat->name)
    ring = sprintf(nil "ro%d_cfet_%s" n plat->name)
    cfetMsg("building %s" tb)
    cv = cfetOpenSchematic(tb)
    vdd = cfetInst(cv "analogLib" "vdc" "VDD" 1.0 5.0)
    cfetSetParams(vdd list(list("vdc" "VDD")))
    inst = cfetInst(cv CFET_LIB_NAME ring "I0" 5.0 4.0)
    cfetInst(cv "analogLib" "gnd" "gnd0" 5.0 0.5)
    cfetConnect(cv vdd "PLUS" "vdd")  cfetConnect(cv vdd "MINUS" "gnd!")
    cfetConnect(cv inst "vdd" "vdd")  cfetConnect(cv inst "vss" "gnd!")
    cfetConnect(cv inst "n1" "out")
    cfetNote(cv 1.0 8.0 sprintf(nil "%s RO%d TB: tran stop=%s maxstep=%s; ic /out=0 (ADE Convergence Aids); Pavg from I(VDD:PLUS)"
                                plat->label n plat->roStop plat->roMaxstep))
    cfetFinish(cv)
    tb))

;; ---------------------------------------------------------------------------
;; 8. Drivers
;; ---------------------------------------------------------------------------
procedure(cfetBuildPlatform(name)
  let((plat)
    plat = cfetPlatform(name)
    unless(plat error("unknown platform %s" name))
    cfetBuildInverter(plat)
    foreach(n cfetRingStages cfetBuildRing(plat n))
    cfetBuildDeviceTB(plat->nCell)
    cfetBuildDeviceTB(plat->pCell)
    cfetBuildInverterTB(plat)
    foreach(n cfetRingStages cfetBuildRingTB(plat n))
    t))

procedure(cfetBuildAll()
  ;; gaa_n is shared by si and sige; its testbench is simply rebuilt (idempotent).
  foreach(plat cfetPlatforms cfetBuildPlatform(plat->name))
  cfetMsg("all schematics built in %s" CFET_LIB_NAME)
  t)

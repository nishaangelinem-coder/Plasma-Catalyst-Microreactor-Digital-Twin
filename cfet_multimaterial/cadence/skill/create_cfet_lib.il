;; =============================================================================
;; create_cfet_lib.il -- SKILL: create the CFET_LIB library, import the nine
;; Verilog-A compact models as `veriloga` cellviews, give each cell a CDF with
;; the UCM-CFET parameter list and build a `symbol` view with terminal order
;; d g s b.
;;
;; Usage (CIW):
;;   load(strcat(getShellEnvVar("CFET_ROOT") "/cadence/skill/create_cfet_lib.il"))
;;   cfetCreateAll()                 ; everything
;;   cfetCreateLib()                 ; only the library
;;   cfetImportVerilogA("gaa_n")     ; one device
;;   cfetCreateSymbol("gaa_n")       ; one symbol
;;
;; Written without access to a Virtuoso installation: every optional / release
;; dependent Cadence function is guarded with isCallable() and a documented
;; fallback is used. Check availability yourself with e.g.
;;   listFunctions("^ahdl")  listFunctions("^schVia")  listFunctions("^va")
;;
;; SKILL style notes: C-style syntax throughout; points are written list(x y)
;; (identical to x:y) and all symbol coordinates are >= 0 so that no negative
;; literal can be mis-read as an infix minus (SKILL parses `list(1 -2)` as
;; `list(1-2)`).
;; =============================================================================

;; ---------------------------------------------------------------------------
;; 0. Configuration
;; ---------------------------------------------------------------------------
;; Root of the cfet_multimaterial checkout (absolute path on the Virtuoso host).
CFET_ROOT = getShellEnvVar("CFET_ROOT") ||
            strcat(getShellEnvVar("HOME")
                   "/Plasma-Catalyst-Microreactor-Digital-Twin/cfet_multimaterial")

CFET_LIB_NAME = "CFET_LIB"
CFET_LIB_PATH = strcat(CFET_ROOT "/cadence/CFET_LIB")
CFET_VA_DIR   = strcat(CFET_ROOT "/veriloga")

;; Technology library to attach (nil = no tech file; CFET_LIB is then a pure
;; schematic/behavioural library, which is all the circuit flow needs).
;; Set to e.g. "cfet_tech" or a foundry tech lib for the conceptual-layout step.
CFET_TECH_LIB = nil

;; The nine device cells; module name == cell name == file basename.
cfetDeviceCells = list("gaa_n" "gaa_p" "sige_p"
                       "mos2_n" "wse2_p"
                       "cnt_n"  "cnt_p"
                       "gan_n"  "gan_p")

;; Device polarity (used for the symbol glyph).
cfetDeviceType = list(
  list("gaa_n" "n") list("gaa_p" "p") list("sige_p" "p")
  list("mos2_n" "n") list("wse2_p" "p")
  list("cnt_n" "n") list("cnt_p" "p")
  list("gan_n" "n") list("gan_p" "p"))

;; Terminal order of every module (also the symbol pin order).
cfetTerminals = list("d" "g" "s" "b")

;; UCM-CFET parameter list (doc/model_spec.md). The CDF default of every
;; parameter is left EMPTY ("") on purpose: an empty, non-stored CDF value is
;; not netlisted, so the material-specific `parameter` default of each .va
;; module wins. build_schematics.il sets the full nominal parameter set on every
;; instance explicitly (cfetDeviceNominal), so the schematics never depend on
;; the module defaults. The third column is the prompt/unit shown in the form;
;; the fourth is the Si-GAA nominal used only for documentation.
cfetParamDefaults = list(
  ;; name     cdfDefault  prompt                                                      Si nominal
  list("W" "" "channel width [m] (ignored when NNS>0: W=NNS*2*(WNS+TNS))" "100n")
  list("L" "" "gate length [m]" "16n")
  list("NNS" "" "number of nanosheets (Si/SiGe), 0 = use W" "0")
  list("WNS" "" "nanosheet width [m]" "20n")
  list("TNS" "" "nanosheet thickness [m]" "5n")
  list("VTH0" "" "threshold voltage magnitude at TNOM [V]" "0.25")
  list("N0" "" "subthreshold ideality factor" "1.1")
  list("ETA" "" "DIBL coefficient [V/V]" "0.05")
  list("MU0" "" "low-field mobility at TNOM [m^2/Vs]" "0.03")
  list("COX" "" "gate oxide capacitance per area [F/m^2]" "0.04")
  list("VSAT" "" "saturation velocity [m/s]" "1e5")
  list("LAMBDA" "" "channel-length-modulation coefficient [1/V]" "0.05")
  list("RSW" "" "source resistance * width [Ohm*m]" "1e-4")
  list("RDW" "" "drain resistance * width [Ohm*m]" "1e-4")
  list("CGSO" "" "gate-source overlap capacitance per width [F/m]" "1e-10")
  list("CGDO" "" "gate-drain overlap capacitance per width [F/m]" "1e-10")
  list("TNOM" "" "nominal temperature [K]" "300")
  list("MUEXP" "" "mobility temperature exponent" "1.5")
  list("KVTH" "" "VTH temperature coefficient [V/K]" "-1e-3")
  list("CQ" "" "quantum capacitance per area [F/m^2] (large = off)" "1e3")
  list("DIT" "" "interface trap density [1/(m^2 eV)]" "0")
  list("RC" "" "contact resistance * width [Ohm*m]" "0")
  list("RTH" "" "thermal resistance [K/W] (GaN self-heating)" "0")
  list("CTH" "" "thermal capacitance [J/K]" "0")
  list("DCNT" "" "CNT density [tubes/m]" "250e6")
  list("FMET" "" "metallic-tube fraction" "0")
  list("TTR" "" "CNT transmission probability" "0.7")
  list("ALPHA" "" "CNT gate-coupling efficiency" "0.6"))

;; ---------------------------------------------------------------------------
;; 1. Helpers
;; ---------------------------------------------------------------------------
procedure(cfetMsg(fmt @rest args)
  printf("[cfet] %s\n" apply('sprintf cons(nil cons(fmt args))))
)

;; Copy a text file line by line using SKILL ports (no shell dependency).
procedure(cfetCopyFile(src dst)
  let((ip op line)
    ip = infile(src)
    unless(ip error("cfetCopyFile: cannot read %s" src))
    op = outfile(dst "w")
    unless(op error("cfetCopyFile: cannot write %s" dst))
    while(gets(line ip) fprintf(op "%s" line))
    close(ip)
    close(op)
    t
  )
)

procedure(cfetDeviceIsP(cell)
  equal(cadr(assoc(cell cfetDeviceType)) "p")
)

;; ---------------------------------------------------------------------------
;; 2. Library creation
;; ---------------------------------------------------------------------------
;; ddCreateLib(t_libName t_path) creates the library directory and adds a
;; DEFINE line to the cds.lib of the current working directory. If the library
;; already exists (e.g. cds.lib.add was appended) it is simply reused.
procedure(cfetCreateLib()
  let((lib)
    lib = ddGetObj(CFET_LIB_NAME)
    if(lib
      then cfetMsg("library %s already exists at %s" CFET_LIB_NAME lib~>readPath)
      else
        cfetMsg("creating library %s at %s" CFET_LIB_NAME CFET_LIB_PATH)
        lib = ddCreateLib(CFET_LIB_NAME CFET_LIB_PATH)
        unless(lib error("ddCreateLib failed for %s" CFET_LIB_NAME))
    )
    ;; Technology: either none (behavioural library) or attach to a tech lib.
    ;; techBindTechFile(d_libId t_techLibName) attaches an existing tech lib;
    ;; the GUI equivalent is CIW Tools -> Technology File Manager -> Attach.
    when(CFET_TECH_LIB
      if(isCallable('techBindTechFile)
        then
          techBindTechFile(lib CFET_TECH_LIB)
          cfetMsg("attached tech library %s" CFET_TECH_LIB)
        else
          cfetMsg("techBindTechFile not available: attach %s via Technology File Manager"
                  CFET_TECH_LIB)
      )
    )
    lib
  )
)

;; ---------------------------------------------------------------------------
;; 3. Verilog-A cellviews
;; ---------------------------------------------------------------------------
;; Two documented ways to turn veriloga/<cell>.va into CFET_LIB/<cell>/veriloga:
;;
;; (a) Portable (default here):
;;     ddGetObj(lib cell "veriloga" "veriloga.va" t) creates the cell, the view
;;     and an (empty) master-file object; its ~>writePath is the OS path we copy
;;     the .va source to. Virtuoso recognises the view type through the master
;;     file name "veriloga.va" (data.reg viewType "veriloga"), exactly as CIW
;;     File -> New -> Cellview with Type "VerilogA" does. Afterwards the
;;     Verilog-A parser must run once to (re)generate the CDF from the module's
;;     `parameter` statements: either open the view in the text editor (Library
;;     Manager double-click) and Save, or call the release-specific ahdl* helper
;;     (cfetParseVerilogA below).
;;
;; (b) vaCreateCellView(t_lib t_cell t_view t_file) -- present in releases that
;;     ship the Verilog-A editor integration. It creates the view, copies the
;;     file, parses it and creates the CDF in one call. Preferred when callable.
;;
;; Both paths leave an existing symbol untouched.
procedure(cfetImportVerilogA(cell)
  let((src fileObj dst)
    src = strcat(CFET_VA_DIR "/" cell ".va")
    unless(isFile(src) error("Verilog-A source not found: %s" src))
    cond(
      (isCallable('vaCreateCellView)
        cfetMsg("%s: vaCreateCellView from %s" cell src)
        vaCreateCellView(CFET_LIB_NAME cell "veriloga" src)
      )
      (t
        cfetMsg("%s: ddGetObj/copy from %s" cell src)
        ;; ddGetObj(lib cell view file g_create): g_create = t creates all
        ;; missing levels (cell, view, file object).
        fileObj = ddGetObj(CFET_LIB_NAME cell "veriloga" "veriloga.va" t)
        unless(fileObj
          error("ddGetObj could not create %s/%s/veriloga" CFET_LIB_NAME cell))
        dst = fileObj~>writePath
        cfetCopyFile(src dst)
        ddUpdateLibList()          ; refresh the library catalogue
        cfetParseVerilogA(cell)
      )
    )
    ;; Explicit CDF so the parameters exist even before the parser ran; the
    ;; parser later overwrites it with the module's own list (same names).
    cfetCreateCDF(cell)
    t
  )
)

;; Run the Virtuoso Verilog-A parser on a veriloga view so that CDF + simInfo
;; are generated. The function name differs between releases; candidates seen
;; in ahdl*.il of various releases: ahdlCompile, ahdlUpdateViewInfo, vaUpdateCDF.
;; None is guaranteed, so we try in order and otherwise ask the user to open the
;; view in the editor and save it once.
procedure(cfetParseVerilogA(cell)
  let((done)
    foreach(fn '(ahdlCompile ahdlUpdateViewInfo vaUpdateCDF)
      when(!done && isCallable(fn)
        cfetMsg("%s: running %s" cell fn)
        errset(funcall(fn CFET_LIB_NAME cell "veriloga") t)
        done = t
      )
    )
    unless(done
      cfetMsg("%s: no Verilog-A parser function found; open %s/%s/veriloga in the"
              cell CFET_LIB_NAME cell)
      cfetMsg("    text editor (Library Manager) and File -> Save once to generate the CDF.")
    )
    done
  )
)

;; ---------------------------------------------------------------------------
;; 4. CDF (Component Description Format)
;; ---------------------------------------------------------------------------
;; The CDF is what the instance property form and the Spectre netlister read.
;; For a veriloga view the netlister emits
;;    <inst> (d g s b) <module> PARAM=value ...
;; so termOrder and instParameters must match the module. The parser-generated
;; CDF selects the AHDL netlist procedure itself; we only create simInfo when it
;; does not exist yet (netlistProcedure nil = default netlister).
procedure(cfetCreateCDF(cell)
  let((cellId cdfId)
    cellId = ddGetObj(CFET_LIB_NAME cell)
    unless(cellId error("cfetCreateCDF: cell %s not found" cell))
    cdfId = cdfGetBaseCellCDF(cellId) || cdfCreateBaseCellCDF(cellId)
    foreach(p cfetParamDefaults
      unless(cdfFindParamByName(cdfId car(p))
        cdfCreateParam(cdfId
          ?name         car(p)
          ?prompt       caddr(p)
          ?type         "string"     ; strings let design-variable expressions through
          ?defValue     cadr(p)
          ?display      "t"
          ?editable     "t"
          ?storeDefault "nil"
        )
      )
    )
    unless(cdfId~>simInfo && cdfId~>simInfo->spectre
      cdfId~>simInfo = list(nil
        'spectre list(nil
          'netlistProcedure  nil
          'instParameters    mapcar('car cfetParamDefaults)
          'termOrder         cfetTerminals
          'componentName     cell
          'propMapping       '(nil)
          'otherParameters   '(model)
          'termMapping       '(nil)
          'stringParameters  '(nil)
          'arrayParameters   '(nil)
          'namePrefix        "X"
          'excludeParameters '(nil)
        )
      )
    )
    cdfId~>instNamePrefix = "X"
    cdfSaveCDF(cdfId)
    cfetMsg("%s: CDF saved (%d parameters)" cell length(cdfId~>parameters))
    cdfId
  )
)

;; ---------------------------------------------------------------------------
;; 5. Symbols
;; ---------------------------------------------------------------------------
;; GUI path (always works): Library Manager -> select the cell -> File -> New ->
;;   Cellview -> Type "From Cellview" (or in the CIW: File -> New -> Cellview,
;;   Tool/Type = "schematicSymbol", "From Cellview"): From View Name =
;;   veriloga, To View Name = symbol. In "Symbol Generation Options" place g on
;;   the Left, d on the Top, s on the Bottom, b on the Right; the pin order of
;;   the generated symbol follows the module port list (d g s b).
;;
;; SKILL alternatives (release dependent, therefore guarded):
;;   * schViaSymbolGen / schViaCreateSymbolFromCellView -- the engine behind the
;;     "From Cellview" dialog. Argument lists changed between IC5 and IC6 and
;;     the symbol-generator package must be loaded (schViaLoadSymGen); it also
;;     reads the port list from the already-parsed veriloga view.
;;   * ahdlGenerateSymbol(lib cell view) -- in some AHDL toolkits; may pop up a
;;     form and is therefore not fully batchable.
;; Caveat: both need the Verilog-A view to be parsed first. When neither is
;; callable (or they fail) the symbol is drawn with documented db*/sch*
;; primitives, which is deterministic and gives d g s b in fixed positions.
procedure(cfetCreateSymbol(cell)
  cond(
    (isCallable('schViaSymbolGen)
      cfetMsg("%s: schViaSymbolGen" cell)
      ;; schViaSymbolGen(lib cell fromView toView leftPins rightPins topPins
      ;;                 bottomPins) -- IC6 signature seen in the field.
      unless(errset(schViaSymbolGen(CFET_LIB_NAME cell "veriloga" "symbol"
                                    list("g") list("b") list("d") list("s")) t)
        cfetMsg("%s: schViaSymbolGen failed, drawing symbol manually" cell)
        cfetDrawSymbol(cell)
      )
    )
    (isCallable('ahdlGenerateSymbol)
      cfetMsg("%s: ahdlGenerateSymbol" cell)
      unless(errset(ahdlGenerateSymbol(CFET_LIB_NAME cell "veriloga") t)
        cfetDrawSymbol(cell)
      )
    )
    (t cfetDrawSymbol(cell))
  )
)

;; Manual symbol on a 0.0625 grid, all coordinates >= 0. Origin = gate pin.
;;   g : (0.0, 0.9)  left          d : (1.5, 1.65) top
;;   s : (1.5, 0.15) bottom        b : (2.0, 0.9)  right
;; Each pin is a 0.125 square on layer ("pin" "drawing") turned into a terminal
;; by schCreateSymbolPin(cv fig name direction). The selection box lives on
;; ("instance" "drawing"); "device annotate" labels show the instance name and
;; parameters.
procedure(cfetDrawSymbol(cell)
  let((cv isP pinFig x y)
    cv = dbOpenCellViewByType(CFET_LIB_NAME cell "symbol" "schematicSymbol" "w")
    unless(cv error("cannot open %s/%s/symbol for writing" CFET_LIB_NAME cell))
    isP = cfetDeviceIsP(cell)
    ;; glyph
    dbCreateLine(cv list("device" "drawing") list(list(0.0 0.9) list(0.7 0.9)))      ; gate lead
    dbCreateLine(cv list("device" "drawing") list(list(0.7 0.4) list(0.7 1.4)))      ; gate electrode
    dbCreateLine(cv list("device" "drawing") list(list(0.85 0.4) list(0.85 1.4)))    ; channel / sheet stack
    dbCreateLine(cv list("device" "drawing") list(list(0.85 1.3) list(1.5 1.3) list(1.5 1.65)))  ; drain
    dbCreateLine(cv list("device" "drawing") list(list(0.85 0.5) list(1.5 0.5) list(1.5 0.15)))  ; source
    dbCreateLine(cv list("device" "drawing") list(list(0.85 0.9) list(2.0 0.9)))     ; body
    if(isP
      then dbCreateEllipse(cv list("device" "drawing") list(list(0.55 0.825) list(0.7 0.975)))  ; p bubble
      else dbCreateLine(cv list("device" "drawing")                                 ; n arrow
             list(list(1.2 0.5) list(1.1 0.6) list(1.1 0.4) list(1.2 0.5)))
    )
    ;; pins, created in module order d g s b
    foreach(spec list(list("d" 1.5 1.65 "inputOutput")
                      list("g" 0.0 0.9  "input")
                      list("s" 1.5 0.15 "inputOutput")
                      list("b" 2.0 0.9  "inputOutput"))
      x = cadr(spec)
      y = caddr(spec)
      pinFig = dbCreateRect(cv list("pin" "drawing")
                 list(list(x - 0.0625  y - 0.0625) list(x + 0.0625  y + 0.0625)))
      schCreateSymbolPin(cv pinFig car(spec) cadddr(spec))
      schCreateSymbolLabel(cv list(x + 0.1  y + 0.1) "pin name" car(spec)
                           "lowerLeft" "R0" "stick" 0.0625)
    )
    ;; selection box and annotation
    dbCreateRect(cv list("instance" "drawing") list(list(0.0 0.0) list(2.1 1.8)))
    schCreateSymbolLabel(cv list(0.0 1.75) "instance name" "[@instanceName]"
                         "lowerLeft" "R0" "stick" 0.0625)
    schCreateSymbolLabel(cv list(0.0 0.0) "device annotate" "[@partName]"
                         "upperLeft" "R0" "stick" 0.0625)
    schCreateSymbolLabel(cv list(2.1 0.3) "device annotate" "[@L:L=%:]"
                         "lowerLeft" "R0" "stick" 0.05)
    schCreateSymbolLabel(cv list(2.1 0.15) "device annotate" "[@W:W=%:]"
                         "lowerLeft" "R0" "stick" 0.05)
    dbReplaceProp(cv "pinOrder" "string" "d g s b")   ; matches termOrder
    dbReplaceProp(cv "partName" "string" cell)
    dbReplaceProp(cv "instNamePrefix" "string" "X")
    dbSave(cv)
    dbClose(cv)
    cfetMsg("%s: manual symbol written" cell)
    t
  )
)

;; ---------------------------------------------------------------------------
;; 6. Driver
;; ---------------------------------------------------------------------------
procedure(cfetReportFunctions()
  foreach(fn '(ddCreateLib ddGetObj vaCreateCellView ahdlCompile ahdlUpdateViewInfo
               vaUpdateCDF schViaSymbolGen ahdlGenerateSymbol schCreateSymbolPin
               schCreateSymbolLabel techBindTechFile)
    cfetMsg("  %-24s %s" fn if(isCallable(fn) "available" "-- not found"))
  )
)

procedure(cfetCreateAll()
  cfetMsg("CFET_ROOT = %s" CFET_ROOT)
  cfetReportFunctions()
  cfetCreateLib()
  foreach(cell cfetDeviceCells
    cfetImportVerilogA(cell)
    cfetCreateSymbol(cell)
  )
  cfetMsg("done: %d device cells in %s" length(cfetDeviceCells) CFET_LIB_NAME)
  t
)

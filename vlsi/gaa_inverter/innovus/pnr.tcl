# pnr.tcl -- Cadence Innovus place-and-route script: mapped netlist -> GDSII
# Invoke:  innovus -init pnr.tcl -log logs/innovus
set DESIGN inverter
set LIB_DIR $env(GAA3_LIB)

# ---- 1. design import ---------------------------------------------------
set init_verilog        ../genus/out/${DESIGN}_netlist.v
set init_top_cell       $DESIGN
set init_lef_file       [list $LIB_DIR/lef/gaa3_tech.lef $LIB_DIR/lef/gaa3_stdcells.lef]
set init_mmmc_file      mmmc.tcl
set init_pwr_net        VDD
set init_gnd_net        VSS
init_design

# ---- 2. floorplan: 6-track cell (168 nm) row, ~60 % utilisation -----------
floorPlan -site gaa3_core -r 1.0 0.60 0.096 0.168 0.096 0.168
globalNetConnect VDD -type pgpin -pin VDD -inst * -verbose
globalNetConnect VSS -type pgpin -pin VSS -inst * -verbose
# follow-pin power rails on M1 (24 nm) straddling the row boundaries
sroute -connect {corePin} -layerChangeRange {M1 M1} -nets {VDD VSS} \
       -corePinTarget {none} -allowJogging 1 -allowLayerChange 0

# ---- 3. placement -------------------------------------------------------------
setPlaceMode -place_global_place_io_pins true
place_opt_design
setPinAssignMode -pinEditInBatch true
editPin -pin a -layer M2 -side Left  -assign 0.000 0.084
editPin -pin y -layer M2 -side Right -assign 0.192 0.084
setPinAssignMode -pinEditInBatch false

# ---- 4. clock (none) / timing-driven optimisation --------------------------
optDesign -preCTS

# ---- 5. routing -----------------------------------------------------------------
setNanoRouteMode -routeWithTimingDriven true -routeWithSiDriven true \
                 -routeTopRoutingLayer 4 -routeBottomRoutingLayer 1
routeDesign
optDesign -postRoute -setup -hold

# ---- 6. fill, verification, extraction -------------------------------------------
addFiller -cell FILL_GAA_X1 -prefix FILL
verify_drc -report reports/drc.rpt
verifyConnectivity -type all -report reports/connectivity.rpt
extractRC
rcOut -spef out/${DESIGN}.spef
timeDesign -postRoute -outDir reports/timing_postroute
report_power -outfile reports/power_postroute.rpt

# ---- 7. deliverables ---------------------------------------------------------------
saveNetlist out/${DESIGN}_pnr.v -includePowerGround
write_sdf   out/${DESIGN}_pnr.sdf
defOut -floorplan -netlist -routing out/${DESIGN}.def
saveDesign  out/${DESIGN}.enc

# ---- 8. GDSII stream-out (Calma GDSII, 1 nm database unit) -------------------------
streamOut out/${DESIGN}.gds \
    -mapFile     ../layout/gaa3.layermap \
    -libName     GAA3_INV_LIB \
    -structureName $DESIGN \
    -merge       [list $LIB_DIR/gds/gaa3_stdcells.gds] \
    -units       1000 \
    -mode        ALL \
    -stripes     1 \
    -uniquifyCellNames
puts "Innovus: streamed out/${DESIGN}.gds"
exit

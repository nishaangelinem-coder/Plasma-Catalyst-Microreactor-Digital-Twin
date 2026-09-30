# synth.tcl -- Cadence Genus synthesis script (RTL -> mapped netlist) for the GAA3 library
# Invoke in the VMware guest:  genus -files synth.tcl -log logs/genus
set DESIGN inverter
set LIB_DIR  $env(GAA3_LIB)                       ;# e.g. /opt/pdk/gaa3/lib
set_db init_lib_search_path  [list $LIB_DIR/liberty $LIB_DIR/lef]
set_db init_hdl_search_path  ../rtl
set_db library    [list gaa3_stdcells_tt_0p70v_25c.lib]
set_db lef_library [list gaa3_tech.lef gaa3_stdcells.lef]
set_db information_level 7
set_db hdl_error_on_blackbox true
set_db syn_generic_effort high
set_db syn_map_effort     high
set_db syn_opt_effort     high

read_hdl -sv ${DESIGN}.v
elaborate $DESIGN
check_design -unresolved
read_sdc constraints.sdc

syn_generic
syn_map
syn_opt

file mkdir out reports
write_hdl        > out/${DESIGN}_netlist.v
write_sdc        > out/${DESIGN}.sdc
write_sdf -edges check_edge -setuphold split -recrem split > out/${DESIGN}.sdf
write_design -innovus -base_name out/${DESIGN}
report_timing -nworst 5 > reports/timing.rpt
report_area           > reports/area.rpt
report_power          > reports/power.rpt
report_gates          > reports/gates.rpt
puts "Genus: mapped $DESIGN onto [get_db [get_db insts] .base_cell.name]"
exit

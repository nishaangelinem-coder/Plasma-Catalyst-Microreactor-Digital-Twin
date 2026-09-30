# synth_ro.tcl -- Genus script for the ring oscillator: keep the combinational loop intact.
# Invoke:  genus -files synth_ro.tcl -log logs/genus_ro
set DESIGN ring_osc
set LIB_DIR  $env(GAA3_LIB)
set_db init_lib_search_path  [list $LIB_DIR/liberty $LIB_DIR/lef]
set_db init_hdl_search_path  ../rtl
set_db library    [list gaa3_stdcells_tt_0p70v_25c.lib]
set_db lef_library [list gaa3_tech.lef gaa3_stdcells.lef]
set_db hdl_preserve_unused_registers true
set_db optimize_constant_0_flops false
read_hdl -sv ${DESIGN}.v
elaborate $DESIGN
# the RTL instantiates INV_GAA_X1 directly: preserve every instance and net, and
# tell timing to break the loop at the enable AND so no false path is optimised away
set_db [get_db insts -if {.base_cell.name == INV_GAA_X1}] .preserve true
set_db [get_db nets *n*] .preserve true
create_clock -name vclk -period 200
set_disable_timing [get_db insts *u_and*]
syn_generic; syn_map; syn_opt
file mkdir out reports
write_hdl > out/${DESIGN}_netlist.v
write_sdc > out/${DESIGN}.sdc
write_design -innovus -base_name out/${DESIGN}
report_gates > reports/ro_gates.rpt
puts "Genus: [llength [get_db insts -if {.base_cell.name == INV_GAA_X1}]] inverter stages preserved"
exit

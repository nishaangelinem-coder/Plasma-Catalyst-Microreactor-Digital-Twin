# constraints.sdc -- timing constraints for the inverter (GAA3 library, 0.7 V, 25 C)
set_units -time ps -capacitance fF
create_clock -name vclk -period 200 ;# virtual clock, 5 GHz budget
set_input_delay  -clock vclk 20 [get_ports a]
set_output_delay -clock vclk 20 [get_ports y]
set_driving_cell -lib_cell INV_GAA_X1 [get_ports a]
set_load 1.28 [get_ports y]          ;# FO4 load: 4 x 0.32 fF INV_GAA_X1 input cap
set_max_transition 15 [current_design]

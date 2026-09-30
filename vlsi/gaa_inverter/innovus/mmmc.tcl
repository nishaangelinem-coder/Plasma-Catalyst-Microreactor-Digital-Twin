# mmmc.tcl -- multi-mode multi-corner setup for the GAA3 kit
create_library_set -name lib_tt -timing [list $env(GAA3_LIB)/liberty/gaa3_stdcells_tt_0p70v_25c.lib]
create_library_set -name lib_ss -timing [list $env(GAA3_LIB)/liberty/gaa3_stdcells_ss_0p63v_125c.lib]
create_library_set -name lib_ff -timing [list $env(GAA3_LIB)/liberty/gaa3_stdcells_ff_0p77v_m40c.lib]
create_rc_corner -name rc_typ -qx_tech_file $env(GAA3_LIB)/qrc/typical/qrcTechFile -T 25
create_delay_corner -name dc_tt -library_set lib_tt -rc_corner rc_typ
create_delay_corner -name dc_ss -library_set lib_ss -rc_corner rc_typ
create_delay_corner -name dc_ff -library_set lib_ff -rc_corner rc_typ
create_constraint_mode -name func -sdc_files [list ../genus/out/inverter.sdc]
create_analysis_view -name av_setup -constraint_mode func -delay_corner dc_ss
create_analysis_view -name av_hold  -constraint_mode func -delay_corner dc_ff
create_analysis_view -name av_typ   -constraint_mode func -delay_corner dc_tt
set_analysis_view -setup [list av_setup av_typ] -hold [list av_hold av_typ]

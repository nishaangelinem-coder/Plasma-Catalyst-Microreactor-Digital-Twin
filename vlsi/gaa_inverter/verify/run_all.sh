#!/bin/bash
# run_all.sh -- regenerate the four GDSII cells, run the reference DRC and LVS, concatenate the reports.
set -e
cd "$(dirname "$0")"
( cd ../layout && python3 gen_gaa_inverter_gds.py && python3 gen_gaa_ro_gds.py && python3 gen_gaa_nand2_gds.py && python3 gen_gaa_sram6t_gds.py )
python3 gaa3_drc.py ../layout/gaa_inverter.gds ../layout/gaa_nand2.gds ../layout/gaa_ro11.gds ../layout/gaa_sram6t.gds
python3 gaa3_lvs.py ../layout/gaa_inverter.gds ../spectre/gaa_inv_tb.scs   INV_GAA_X1     > /dev/null
python3 gaa3_lvs.py ../layout/gaa_nand2.gds    ../spectre/gaa_nand2_tb.scs NAND2_GAA_X1   > /dev/null
python3 gaa3_lvs.py ../layout/gaa_ro11.gds     ro11_sch.scs                RO11_GAA       > /dev/null
python3 gaa3_lvs.py ../layout/gaa_sram6t.gds   ../spectre/gaa_sram6t_tb.scs SRAM6T_GAA_HD > /dev/null
cat gaa_inverter.drc.sum gaa_nand2.drc.sum gaa_ro11.drc.sum gaa_sram6t.drc.sum > gaa3_drc_all.sum
cat gaa_inverter.lvs.rpt gaa_nand2.lvs.rpt gaa_ro11.lvs.rpt gaa_sram6t.lvs.rpt > gaa3_lvs_all.rpt
grep -h "RESULT" gaa3_lvs_all.rpt; grep -h "DRC STATUS" gaa3_drc_all.sum

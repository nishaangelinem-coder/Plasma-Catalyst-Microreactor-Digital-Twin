#!/bin/bash
# run_lvs.sh -- Calibre LVS: GDS vs. the Spectre/CDL netlist of ring_osc_top
set -euo pipefail
source "$(dirname "$0")/env.sh"
GDS=${1:-$PROJ_ROOT/cadence/layout/ring_osc_top.gds}
CDL=${2:-$PROJ_ROOT/cadence/layout/ring_osc_top.cdl}
CELL=${3:-ring_osc_top}
RULES=$PDK_ROOT/calibre/lvs/calibre.lvs
cd "$PROJ_ROOT/cadence/layout"
cat > lvs.runset <<EOR
LAYOUT PATH "$GDS"
LAYOUT PRIMARY "$CELL"
LAYOUT SYSTEM GDSII
SOURCE PATH "$CDL"
SOURCE PRIMARY "$CELL"
SOURCE SYSTEM SPICE
LVS REPORT "lvs_report.rep"
MASK SVDB DIRECTORY "svdb" QUERY XRC
INCLUDE "$RULES"
EOR
calibre -lvs -hier -spice svdb/$CELL.sp -64 lvs.runset | tee lvs.log
grep -E "CORRECT|INCORRECT" lvs_report.rep || true

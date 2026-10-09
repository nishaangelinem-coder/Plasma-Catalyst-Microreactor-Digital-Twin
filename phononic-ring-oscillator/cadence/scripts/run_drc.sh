#!/bin/bash
# run_drc.sh -- Calibre DRC on the streamed-out GDS (edit RULE file path for your PDK)
set -euo pipefail
source "$(dirname "$0")/env.sh"
GDS=${1:-$PROJ_ROOT/cadence/layout/ring_osc_top.gds}
CELL=${2:-ring_osc_top}
RULES=$PDK_ROOT/calibre/drc/calibre.drc
cd "$PROJ_ROOT/cadence/layout"
cat > drc.runset <<EOR
LAYOUT PATH "$GDS"
LAYOUT PRIMARY "$CELL"
LAYOUT SYSTEM GDSII
DRC RESULTS DATABASE "drc_results.db" ASCII
DRC SUMMARY REPORT "drc_summary.rep" REPLACE
INCLUDE "$RULES"
EOR
calibre -drc -hier -64 -turbo 4 drc.runset | tee drc.log
grep -A3 "RULECHECK RESULTS" drc_summary.rep || true

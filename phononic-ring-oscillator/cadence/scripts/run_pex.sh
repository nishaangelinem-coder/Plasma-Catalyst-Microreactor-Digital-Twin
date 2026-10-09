#!/bin/bash
# run_pex.sh -- parasitic extraction (Calibre xRC; use Quantus QRC from Virtuoso as alternative)
set -euo pipefail
source "$(dirname "$0")/env.sh"
CELL=${1:-ring_osc_top}
RULES=$PDK_ROOT/calibre/xrc/calibre.rcx
cd "$PROJ_ROOT/cadence/layout"
cat > pex.runset <<EOR
LAYOUT PATH "ring_osc_top.gds"
LAYOUT PRIMARY "$CELL"
SOURCE PATH "ring_osc_top.cdl"
SOURCE PRIMARY "$CELL"
MASK SVDB DIRECTORY "svdb" QUERY XRC
PEX NETLIST "${CELL}_pex.sp" HSPICE 1 SOURCENAMES
PEX EXTRACT INCLUDE "$RULES"
INCLUDE "$RULES"
EOR
calibre -xrc -phdb -64 pex.runset && calibre -xrc -pdb -rcc -64 pex.runset && calibre -xrc -fmt -64 pex.runset | tee pex.log
echo "extracted netlist: cadence/layout/${CELL}_pex.sp  -> re-run PSS/Pnoise with it (see docs)"

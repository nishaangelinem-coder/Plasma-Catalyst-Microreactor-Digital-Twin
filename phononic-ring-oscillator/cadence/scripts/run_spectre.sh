#!/bin/bash
# run_spectre.sh -- bare Spectre run of a testbench (no Virtuoso needed)
# usage: scripts/run_spectre.sh netlists/ring_osc_tb.scs
set -euo pipefail
source "$(dirname "$0")/env.sh"
TB=${1:-netlists/ring_osc_tb.scs}
cd "$PROJ_ROOT/cadence"
NAME=$(basename "$TB" .scs)
# substitute PDK path/section placeholders into a working copy
sed -e "s|\$PDK_MODEL_FILE|$PDK_MODEL_FILE|g" -e "s|\$PDK_SECTION|$PDK_SECTION|g" "$TB" > results/${NAME}.run.scs
cd results
spectre +aps +mt=4 ${NAME}.run.scs -format psfascii -raw ${NAME}.raw +log ${NAME}.log
echo "done: cadence/results/${NAME}.raw  (log: ${NAME}.log)"

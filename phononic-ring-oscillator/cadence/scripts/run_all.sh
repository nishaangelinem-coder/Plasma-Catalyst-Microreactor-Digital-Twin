#!/bin/bash
# run_all.sh -- full pre-layout characterisation in headless OCEAN
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJ_ROOT/cadence/ocean"
for s in run_stb.ocn run_tran_startup.ocn run_pss_pnoise.ocn run_pvt_corners.ocn run_montecarlo.ocn; do
  echo "=== $s ==="; ocean -nograph -replay "$s" 2>&1 | tee "../results/${s%.ocn}.log"
done
cd "$PROJ_ROOT"
python3 sim/collect_cadence_results.py && python3 sim/make_figures.py && make -C paper

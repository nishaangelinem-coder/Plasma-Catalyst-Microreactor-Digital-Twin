#!/bin/bash
# continuation: wait for the VDD/temperature sweeps, then sensitivity and Monte Carlo
while pgrep -f "sim.run_sweeps" > /dev/null; do sleep 20; done
set -x
python3 -m sim.run_sensitivity      > results/log_sensitivity.txt 2>&1
python3 -m sim.run_montecarlo 150 1000 > results/log_montecarlo.txt 2>&1
echo PIPELINE_DONE

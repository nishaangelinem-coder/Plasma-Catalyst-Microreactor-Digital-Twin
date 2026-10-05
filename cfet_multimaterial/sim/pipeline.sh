#!/bin/bash
# Full circuit-validation pipeline after calibration (run from cfet_multimaterial/)
set -x
python3 -m sim.run_nominal gan      > results/log_nominal_gan.txt 2>&1
python3 -m sim.run_sweeps           > results/log_sweeps.txt 2>&1
python3 -m sim.run_sensitivity      > results/log_sensitivity.txt 2>&1
python3 -m sim.run_montecarlo 200 1000 > results/log_montecarlo.txt 2>&1
echo PIPELINE_DONE

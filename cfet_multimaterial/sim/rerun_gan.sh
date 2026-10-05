#!/bin/bash
python3 -m sim.run_sweeps gan > results/log_sweeps_gan.txt 2>&1
python3 -m sim.run_nominal gan > results/log_nominal_gan2.txt 2>&1
echo GAN_RERUN_DONE >> results/log_sweeps_gan.txt

# Phononic ring-resonator oscillator with a CMOS sustaining amplifier

Full co-design of a 1-GHz oscillator built around the new low-loss SiN-on-LN
phononic ring resonator (Ji et al., arXiv:2603.27711, 2026: f0 = 1001.15 MHz,
Q_L = 17 925, Q_i = 22 393, Q_c = 179 680, 28.2-dB insertion loss in 50 ohm) and a
180-nm CMOS transmission-mode sustaining amplifier.

```
veriloga/   phononic_ring_resonator.va   extended mBVD + delay-element Verilog-A model
sim/        open-source pipeline (Python + ngspice): model, amplifier design, phase noise,
            Monte Carlo, temperature, figure and number generation
cadence/    Spectre netlists, OCEAN scripts (stb, tran, PSS/Pnoise, PVT, MC), Calibre
            DRC/LVS/PEX run scripts, layout plan, SKILL floorplan helper
paper/      IEEE TCAS-I manuscript (LaTeX, IEEEtran) with auto-generated figures/numbers
docs/       VMware + Cadence setup guide, patent disclosure draft
results/    JSON summaries and raw ngspice outputs
```

## Reproduce (no Cadence needed)

```bash
pip install numpy scipy matplotlib
sudo apt-get install ngspice texlive-latex-base texlive-latex-extra texlive-publishers texlive-science
cd phononic-ring-oscillator
python3 sim/ngspice_osc.py        # transistor-level open loop, noise, start-up (~10 min)
python3 sim/make_figures.py       # all figures, tables, paper/numbers.tex
make -C paper                     # paper/main.pdf
```

## Cadence flow (VMware guest, see docs/VMWARE_CADENCE_SETUP.md)

```bash
source cadence/scripts/env.sh     # edit paths once
cadence/scripts/run_all.sh        # stb, tran, PSS/Pnoise, corners, MC -> cadence/results/*.csv
python3 sim/collect_cadence_results.py && python3 sim/make_figures.py && make -C paper
```

Every number in the manuscript is produced by this pipeline; the Spectre results
overlay the model curves automatically once `cadence/results/` is populated.

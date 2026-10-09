# CMOS-Driven Nonreciprocal Acoustic Circulator (STM LiNbO3 resonator loop)

Complete, reproducible design study of a chip-scale, magnet-free, inductor-less
circulator for full-duplex RF front-ends: three LiNbO3 laterally-vibrating
resonators in a capacitively coupled loop, frequency-modulated by MOS varactors
that are driven with 0/120/240-degree phases from a 65 nm CMOS divide-by-six
Johnson counter and tapered drivers.

**Everything here is simulation.** No device was fabricated and no measurement was
made. The cloud environment that produced this work has no access to Cadence; all
circuit results come from ngspice (transistor level, BSIM4 65 nm-class card) and a
conversion-matrix periodic S-parameter solver (the analysis Spectre performs with
PSS+PSP). Cadence/Spectre/OCEAN/SKILL files are provided to regenerate the results
in Virtuoso on the user's VMware machine (`cadence/README.md`).

## Layout of this folder

```
sim/        Python: LTP solver (ltp.py), circuit (circulator.py, topologies.py), CMT (cmt.py),
            design search, ngspice harness, analysis/figures, schematics, Cadence export
spice/      ngspice netlists: CMOS block library, phase-generator bench, varactor C-V bench
models/     65 nm-class BSIM4 model card (predictive; not a foundry model)
cadence/    Spectre netlists, OCEAN PSS/PSP script, SKILL schematic generator, VM flow README
layout/     gdstk layout generator, GDSII, KLayout render script
figures/    schematics, waveforms, S-parameters, design space, layout renders (PNG + PDF)
results/    JSON/CSV: design point, LTP summary, ngspice summary, CMT design rules, searches
paper/      IEEE TMTT manuscript (IEEEtran LaTeX) + verified bibliography + compiled PDF
docs/       reference verification status, honest-scope notes
tests/      unit tests (solver vs analytic sideband, CMT vs LTP, Johnson counter phases)
```

## Reproduce

```bash
pip install numpy scipy matplotlib schemdraw gdstk scikit-rf
sudo apt-get install ngspice klayout texlive-latex-extra texlive-publishers texlive-bibtex-extra
cd acoustic-circulator
python3 sim/cmt_design_rules.py              # normalised CMT optimum (Table I)
python3 sim/design_search.py A varactor 500  # global search (also B/C, switch)
python3 sim/finalize_design.py               # pick design point -> results/design_final.json
python3 sim/analysis.py                      # LTP S-params, CMT fit, design-space figures
python3 sim/run_ngspice_sweep.py 41          # transistor-level co-simulation (~20-40 min on 4 cores)
python3 sim/schematics.py && python3 layout/gen_layout.py && (cd layout && klayout -zz -r render_klayout.py)
python3 sim/cadence_export.py && python3 sim/make_numbers.py
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main
python3 -m pytest -q tests
```

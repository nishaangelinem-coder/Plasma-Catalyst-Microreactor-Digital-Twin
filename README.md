# Plasma-Catalyst Microreactor Digital Twin (PC-HDT)

An open-source, fully reproducible in-silico study of **digital twins for DBD
plasma-catalytic NH₃ microreactors powered by intermittent renewable electricity**.

It contains

* a high-fidelity *virtual plant* (`pcmr/plant.py`) — axially resolved packed-bed DBD
  reactor with Manley power law, plasma-catalytic + radical NH₃ formation,
  electron-impact/thermal decomposition, catalyst sintering, plasma nitridation,
  burning-voltage ageing, an unannounced poisoning event and realistic sensor noise;
* the proposed **Physics-Constrained Hybrid Digital Twin (PC-HDT)** (`pcmr/twins.py`)
  and a **risk- and degradation-aware twin-in-the-loop optimiser** (`pcmr/control.py`);
* seven existing twin/modelling approaches and four existing control strategies as
  baselines, plus ablations;
* experiment scripts that write every reading to `results/` and every figure to `figures/`.

## Reproduce

```bash
pip install -r requirements.txt
python -m pytest -q tests                  # unit tests
python experiments/run_experiments.py      # E1–E4, 20 held-out seeds (~15–25 min on 4 cores)
python experiments/make_figures.py         # figures/fig1..fig6
```

`--quick` runs 3 seeds for a smoke test.

> **Important:** every number in this repository comes from simulation (in-silico
> experiments against a virtual plant), **not** from laboratory measurements. The
> virtual plant is parameterised to reproduce value ranges typical of DBD
> plasma-catalytic NH₃ literature; it has not been calibrated against a specific
> physical reactor. See §9 of the report for the recommended hardware validation plan.

## Layout

```
pcmr/            package: plant, reduced twin model, twins, controllers, scenarios
experiments/     run_experiments.py (E1–E4), make_figures.py
results/         CSV readings, per-seed metrics, summaries, Wilcoxon tests, traces
figures/         publication figures (300 dpi PNG)
docs/            RESEARCH_REPORT.md
tests/           unit tests
```


## Second study in this repository: photon-to-phonon neonatal brain monitor

`neonatal_photoacoustic_monitor/` contains an independent, fully reproducible in-silico
design study of a wearable / bedside **photoacoustic monitor of neonatal cerebral
venous oxygenation and brain temperature** (transfontanelle, superior sagittal sinus),
with its own package (`p2pneo`), experiments, results, figures and the full paper in
`neonatal_photoacoustic_monitor/docs/`. See its README for details.

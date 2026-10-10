# Photon-to-Phonon Neonatal Brain Monitor (p2pneo)

An open, fully reproducible **in-silico design study** of a wearable / bedside
*photoacoustic* ("photon-to-phonon") monitor that reads **cerebral venous oxygen
saturation** and **brain temperature** of a neonate through the anterior fontanelle,
targeting the superior sagittal sinus.

Pulsed near-infrared **photons** (4 wavelengths) are absorbed by haemoglobin; the
thermo-elastic expansion launches ultrasonic **phonons** that a 3-MHz transducer on the
fontanelle records. The spectrum of the depth-gated signal gives venous sO2; the
temperature dependence of the Grüneisen parameter of blood and the temperature
dependence of the speed of sound (pulse-echo shift) give brain temperature. A joint
extended Kalman filter fuses both with an on-probe reference absorber and the probe
thermistor.

Contents

* `p2pneo/` – tissue optics, numba Monte Carlo (layered, partial path lengths), fluence
  table + perturbation model, acoustic forward model (generation, propagation,
  transducer, noise, gating, echo shift), Pennes thermal-safety model, virtual neonate
  with clinical scenarios, the proposed estimator and baselines, metrics.
* `experiments/` – `build_fluence_table.py` (Monte Carlo, ~10 min on 4 cores),
  `run_design.py` (E1 optical, E2 acoustic, E6 safety/power), `run_dynamic.py`
  (E3 static accuracy, E4 clinical scenarios, E5 sensitivity; ~1-1.5 h on 4 cores),
  `make_figures.py`.
* `results/` – every reading as CSV/NPZ, summaries, Wilcoxon tests.
* `figures/` – publication figures (300 dpi).
* `docs/` – the full paper (Markdown + DOCX + PDF).
* `tests/` – unit tests.

## Reproduce

```bash
pip install -r ../requirements.txt numba
python -m pytest -q tests
python experiments/build_fluence_table.py          # results/fluence_table.npz
python experiments/run_design.py                   # E1, E2, E6
python experiments/run_dynamic.py                  # E3, E4, E5   (--quick for a smoke test)
python experiments/make_figures.py
```

> **Important.** Every number in this folder is produced by simulation against a
> virtual neonate whose hidden parameters differ from the estimator's population
> model. No laboratory, phantom, animal or clinical measurement is included. The
> literature values used to parameterise the model (extinction coefficients, tissue
> optical and acoustic properties, Grüneisen temperature coefficients, speed-of-sound
> temperature coefficients) must be re-checked before any hardware work, and the
> device must be validated on phantoms, in animals and in a clinical study before any
> clinical claim is made.

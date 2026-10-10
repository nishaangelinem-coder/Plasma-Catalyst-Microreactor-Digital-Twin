"""p2pneo - in-silico design study of a wearable/bedside photon-to-phonon
(photoacoustic) monitor for neonatal cerebral oxygenation and brain temperature.

Modules
-------
tissue        chromophore spectra, layered neonatal head model, optical properties
mc            numba Monte Carlo photon transport (layered, pencil beam, partial path lengths)
fluence       fluence/reflectance tables, Born/Beer-Lambert perturbation for chromophore changes
acoustic      photoacoustic generation, 1-D acoustic propagation, transducer, noise, gating, TOF
thermal       1-D Pennes bioheat model for optical/electronic heating safety
subject       virtual neonate (hidden truth) and clinical scenarios
estimators    proposed joint EKF (PA + echo-shift + reference absorber) and baselines
metrics       error metrics, Bland-Altman, event detection, Wilcoxon helpers
"""
__version__ = "0.1.0"
